import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.expenses.domain.value_objects import ExpenseStatus
from app.sales.domain.value_objects import SalePaymentStatus, SaleStatus

# total_amount/payment_status are derived (not stored columns), so period
# filtering can't happen in SQL — same accepted tradeoff as
# sales/application/queries/list_outstanding_sales.py:_MAX_SALES_TO_SCAN.
_MAX_SALES_TO_SCAN = 10_000
_MAX_EXPENSES_TO_SCAN = 10_000


@dataclass(frozen=True)
class GetDashboardSummaryQuery:
    business_id: uuid.UUID
    start_date: date | None = None
    end_date: date | None = None


@dataclass(frozen=True)
class DashboardSummary:
    total_revenue: Decimal
    total_expenses: Decimal
    net_profit: Decimal
    outstanding_receivables: Decimal
    period_start: date | None
    period_end: date | None


def _in_range(value: date, start: date | None, end: date | None) -> bool:
    if start is not None and value < start:
        return False
    if end is not None and value > end:
        return False
    return True


class GetDashboardSummaryUseCase:
    """Cross-context aggregation over Sale and Expense — pure orchestration
    of existing aggregates, no new persisted concept, so this module has no
    domain/infrastructure layer of its own (same deviation as data_import,
    see the Slice 7 plan for the reasoning).

    total_revenue/total_expenses/net_profit are scoped to [start_date,
    end_date]; outstanding_receivables is a point-in-time balance (what's
    currently owed) and is deliberately NOT period-scoped.
    """

    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: GetDashboardSummaryQuery) -> DashboardSummary:
        sales, _ = await self._uow.sales.list_for_business(
            query.business_id, offset=0, limit=_MAX_SALES_TO_SCAN
        )
        expenses, _ = await self._uow.expenses.list_for_business(
            query.business_id, offset=0, limit=_MAX_EXPENSES_TO_SCAN
        )

        total_revenue = sum(
            (
                sale.total_amount.amount
                for sale in sales
                if sale.status != SaleStatus.VOID
                and _in_range(sale.invoice_date, query.start_date, query.end_date)
            ),
            Decimal("0"),
        )
        total_expenses = sum(
            (
                expense.total_amount.amount
                for expense in expenses
                if expense.status != ExpenseStatus.VOID
                and _in_range(expense.expense_date, query.start_date, query.end_date)
            ),
            Decimal("0"),
        )
        outstanding_receivables = sum(
            (
                sale.outstanding_amount.amount
                for sale in sales
                if sale.status != SaleStatus.VOID and sale.payment_status != SalePaymentStatus.PAID
            ),
            Decimal("0"),
        )

        return DashboardSummary(
            total_revenue=total_revenue,
            total_expenses=total_expenses,
            net_profit=total_revenue - total_expenses,
            outstanding_receivables=outstanding_receivables,
            period_start=query.start_date,
            period_end=query.end_date,
        )
