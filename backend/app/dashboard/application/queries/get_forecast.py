import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.dashboard.application.queries.get_dashboard_trend import (
    GetDashboardTrendQuery,
    GetDashboardTrendUseCase,
)
from app.shared.application.ports import IClock

# Fixed lookback/horizon, not user-configurable — forecasting is a monthly
# concept for a small business, unlike the Reports page's day/week/month
# choice. 6 months of history is enough for a linear trend to mean
# something; 3 months forward keeps the extrapolation short and honest.
_HISTORY_MONTHS = 6
_FORECAST_MONTHS = 3


@dataclass(frozen=True)
class GetForecastQuery:
    business_id: uuid.UUID


@dataclass(frozen=True)
class ForecastPoint:
    period_start: date
    projected_revenue: Decimal
    projected_expenses: Decimal
    projected_net_profit: Decimal


@dataclass(frozen=True)
class Forecast:
    history_months_used: int
    points: list[ForecastPoint]


def _add_months(value: date, months: int) -> date:
    total = (value.year * 12 + (value.month - 1)) + months
    year, month = divmod(total, 12)
    return date(year, month + 1, 1)


def _fit_line(xs: list[int], ys: list[float]) -> tuple[float, float]:
    """Ordinary least squares. Returns (intercept, slope). The historical
    window always has _HISTORY_MONTHS distinct x-values, so the denominator
    below can never be zero — no guard needed.
    """
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    return intercept, slope


def _to_money(value: float) -> Decimal:
    return Decimal(str(round(max(value, 0.0), 2)))


class GetForecastUseCase:
    """Projects revenue/expenses forward via ordinary least-squares linear
    regression over the last _HISTORY_MONTHS completed months, reusing
    GetDashboardTrendUseCase for the historical series rather than
    re-querying Sale/Expense directly — same cross-context-reuse pattern
    GetBusinessHealthScoreUseCase already uses for GetDashboardSummaryUseCase.

    The current, in-progress month is deliberately excluded from the
    regression input (mirrors GetBusinessHealthScoreUseCase's own
    this_month_start/last_month_start split) so a partial month doesn't
    skew the trend low. Regression runs in plain float — this is a
    statistical approximation, not a ledger computation — and results are
    re-quantized to Decimal cents. Projected revenue/expenses are floored
    at 0 (can't be negative); projected net profit is not floored, since a
    projected loss is a real signal worth showing.

    Uses `clock.now()` rather than `date.today()` so this stays
    deterministically unit-testable via the existing FakeClock fake.
    """

    def __init__(self, uow: AppUnitOfWork, clock: IClock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, query: GetForecastQuery) -> Forecast:
        today = self._clock.now().date()
        current_month_start = date(today.year, today.month, 1)
        last_completed_month_end = current_month_start - timedelta(days=1)
        history_start = _add_months(
            date(last_completed_month_end.year, last_completed_month_end.month, 1),
            -(_HISTORY_MONTHS - 1),
        )

        trend = await GetDashboardTrendUseCase(self._uow).execute(
            GetDashboardTrendQuery(
                business_id=query.business_id,
                start_date=history_start,
                end_date=last_completed_month_end,
                granularity="month",
            )
        )

        xs = list(range(len(trend.points)))
        revenue_intercept, revenue_slope = _fit_line(xs, [float(p.revenue) for p in trend.points])
        expenses_intercept, expenses_slope = _fit_line(xs, [float(p.expenses) for p in trend.points])

        points = []
        for i in range(_FORECAST_MONTHS):
            x = len(xs) + i
            projected_revenue = _to_money(revenue_intercept + revenue_slope * x)
            projected_expenses = _to_money(expenses_intercept + expenses_slope * x)
            points.append(
                ForecastPoint(
                    period_start=_add_months(current_month_start, i),
                    projected_revenue=projected_revenue,
                    projected_expenses=projected_expenses,
                    projected_net_profit=projected_revenue - projected_expenses,
                )
            )

        return Forecast(history_months_used=len(trend.points), points=points)
