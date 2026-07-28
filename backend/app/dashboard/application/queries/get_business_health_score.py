import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.dashboard.application.queries.get_dashboard_summary import (
    DashboardSummary,
    GetDashboardSummaryQuery,
    GetDashboardSummaryUseCase,
)
from app.inventory.application.queries.list_products import ListProductsQuery, ListProductsUseCase
from app.shared.application.pagination import PageRequest
from app.shared.application.ports import IClock

# Each sub-score is a 0..1 fraction; the overall score is the average of
# whichever sub-scores are applicable (see the docstrings below for when a
# category is excluded) — this naturally rescales without needing explicit
# weight bookkeeping.
_PROFIT_MARGIN_CEILING = Decimal("0.30")
_REVENUE_GROWTH_CEILING = Decimal("0.20")
_REVENUE_GROWTH_FLOOR = Decimal("-0.20")

_LABEL_BANDS: list[tuple[int, str]] = [
    (80, "Excellent"),
    (60, "Good"),
    (40, "Fair"),
    (20, "Needs attention"),
]
_LOWEST_LABEL = "Critical"


@dataclass(frozen=True)
class GetBusinessHealthScoreQuery:
    business_id: uuid.UUID


@dataclass(frozen=True)
class BusinessHealthScore:
    overall_score: int
    label: str
    # None for any category excluded from the average (see
    # GetBusinessHealthScoreUseCase's docstring) — the frontend renders
    # "Not enough data yet" for those rather than a fabricated number.
    breakdown: dict[str, float | None]


def _clamp(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return max(low, min(high, value))


def _label_for(score: int) -> str:
    for threshold, label in _LABEL_BANDS:
        if score >= threshold:
            return label
    return _LOWEST_LABEL


class GetBusinessHealthScoreUseCase:
    """Deterministic, formula-based 0-100 score — no AI call, so it's a
    reliable number an AI Insights slice can later explain rather than the
    only source of truth for. Cross-context by nature (reuses
    GetDashboardSummaryUseCase and ListProductsUseCase), same "no domain
    layer" deviation as the rest of the dashboard module.

    Uses `clock.now()` rather than `date.today()` so this stays
    deterministically unit-testable via the existing FakeClock fake.
    """

    def __init__(self, uow: AppUnitOfWork, clock: IClock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, query: GetBusinessHealthScoreQuery) -> BusinessHealthScore:
        today = self._clock.now().date()
        this_month_start = date(today.year, today.month, 1)
        last_month_end = this_month_start - timedelta(days=1)
        last_month_start = date(last_month_end.year, last_month_end.month, 1)

        this_month = await GetDashboardSummaryUseCase(self._uow).execute(
            GetDashboardSummaryQuery(
                business_id=query.business_id, start_date=this_month_start, end_date=today
            )
        )
        last_month = await GetDashboardSummaryUseCase(self._uow).execute(
            GetDashboardSummaryQuery(
                business_id=query.business_id, start_date=last_month_start, end_date=last_month_end
            )
        )

        breakdown: dict[str, float | None] = {
            "profitability": self._profitability(this_month),
            "revenue_trend": self._revenue_trend(this_month, last_month),
            "receivables_health": self._receivables_health(this_month),
            "inventory_health": await self._inventory_health(query.business_id),
        }

        applicable = [v for v in breakdown.values() if v is not None]
        overall = round(100 * (sum(applicable) / len(applicable))) if applicable else 0

        return BusinessHealthScore(overall_score=overall, label=_label_for(overall), breakdown=breakdown)

    def _profitability(self, this_month: DashboardSummary) -> float | None:
        if this_month.total_revenue <= 0:
            return None
        margin = this_month.net_profit / this_month.total_revenue
        return float(_clamp(margin / _PROFIT_MARGIN_CEILING, Decimal("0"), Decimal("1")))

    def _revenue_trend(self, this_month: DashboardSummary, last_month: DashboardSummary) -> float:
        if last_month.total_revenue <= 0:
            return 1.0 if this_month.total_revenue > 0 else 0.5

        growth = (this_month.total_revenue - last_month.total_revenue) / last_month.total_revenue
        span = _REVENUE_GROWTH_CEILING - _REVENUE_GROWTH_FLOOR
        return float(_clamp((growth - _REVENUE_GROWTH_FLOOR) / span, Decimal("0"), Decimal("1")))

    def _receivables_health(self, this_month: DashboardSummary) -> float:
        if this_month.total_revenue <= 0:
            return 0.0 if this_month.outstanding_receivables > 0 else 1.0

        ratio = this_month.outstanding_receivables / this_month.total_revenue
        return float(_clamp(Decimal("1") - ratio, Decimal("0"), Decimal("1")))

    async def _inventory_health(self, business_id: uuid.UUID) -> float | None:
        # PageRequest caps limit at 200 (shared/application/pagination.py) —
        # same accepted scale limit already applied in
        # ai_assistant/application/tools.py's list_low_stock_products tool.
        page = await ListProductsUseCase(self._uow).execute(
            ListProductsQuery(business_id=business_id, page=PageRequest(offset=0, limit=200))
        )
        if not page.items:
            return None

        healthy = sum(1 for p in page.items if not (p.is_low_stock or p.is_out_of_stock))
        return healthy / len(page.items)
