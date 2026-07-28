import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.expenses.domain.value_objects import ExpenseStatus
from app.sales.domain.value_objects import SaleStatus

# Same accepted tradeoff as get_dashboard_summary.py — total_amount isn't a
# stored column, so bucketing can't happen in SQL.
_MAX_SALES_TO_SCAN = 10_000
_MAX_EXPENSES_TO_SCAN = 10_000

Granularity = Literal["day", "week", "month"]


@dataclass(frozen=True)
class GetDashboardTrendQuery:
    business_id: uuid.UUID
    start_date: date
    end_date: date
    # None preserves the auto-infer behavior the dashboard chart relies on
    # (day for <=31 days, else month) — the Reports page (Slice 3) is the
    # only caller that ever passes this explicitly, since a report's
    # granularity is a user choice independent of the date range.
    granularity: Granularity | None = None


@dataclass(frozen=True)
class TrendPoint:
    period_start: date
    revenue: Decimal
    expenses: Decimal


@dataclass(frozen=True)
class DashboardTrend:
    granularity: Granularity
    points: list[TrendPoint]


def _week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _bucket_key(value: date, granularity: Granularity) -> date:
    if granularity == "day":
        return value
    if granularity == "week":
        return _week_start(value)
    return date(value.year, value.month, 1)


def _generate_buckets(start: date, end: date, granularity: Granularity) -> list[date]:
    if granularity == "day":
        days = (end - start).days
        return [start + timedelta(days=i) for i in range(days + 1)]

    if granularity == "week":
        current = _week_start(start)
        last = _week_start(end)
        buckets = []
        while current <= last:
            buckets.append(current)
            current += timedelta(days=7)
        return buckets

    buckets = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        buckets.append(date(year, month, 1))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return buckets


class GetDashboardTrendUseCase:
    """Cross-context aggregation over Sale and Expense, same deviation from
    the 4-layer template as get_dashboard_summary.py (pure orchestration,
    no new persisted concept).

    Unlike the summary query, start_date/end_date are both required — a
    time series needs a finite set of buckets to plot. Granularity is
    inferred from the span by default (day for <=31 days, else month), but
    can be requested explicitly (day/week/month) — used by the Reports
    page (Slice 3), where granularity is a user choice independent of the
    date range. The response always reports whichever granularity was
    actually used, so it's never ambiguous to the caller.
    """

    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: GetDashboardTrendQuery) -> DashboardTrend:
        if query.granularity is not None:
            granularity: Granularity = query.granularity
        else:
            granularity = "day" if (query.end_date - query.start_date).days <= 31 else "month"

        sales, _ = await self._uow.sales.list_for_business(
            query.business_id, offset=0, limit=_MAX_SALES_TO_SCAN
        )
        expenses, _ = await self._uow.expenses.list_for_business(
            query.business_id, offset=0, limit=_MAX_EXPENSES_TO_SCAN
        )

        buckets = _generate_buckets(query.start_date, query.end_date, granularity)
        revenue_by_bucket: dict[date, Decimal] = dict.fromkeys(buckets, Decimal("0"))
        expenses_by_bucket: dict[date, Decimal] = dict.fromkeys(buckets, Decimal("0"))

        for sale in sales:
            if sale.status == SaleStatus.VOID:
                continue
            if not (query.start_date <= sale.invoice_date <= query.end_date):
                continue
            key = _bucket_key(sale.invoice_date, granularity)
            revenue_by_bucket[key] += sale.total_amount.amount

        for expense in expenses:
            if expense.status == ExpenseStatus.VOID:
                continue
            if not (query.start_date <= expense.expense_date <= query.end_date):
                continue
            key = _bucket_key(expense.expense_date, granularity)
            expenses_by_bucket[key] += expense.total_amount.amount

        points = [
            TrendPoint(
                period_start=bucket,
                revenue=revenue_by_bucket[bucket],
                expenses=expenses_by_bucket[bucket],
            )
            for bucket in buckets
        ]
        return DashboardTrend(granularity=granularity, points=points)
