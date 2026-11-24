import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.sales.application.ports import SalesUnitOfWork
from app.sales.application.queries.list_outstanding_sales import (
    ListOutstandingSalesQuery,
    ListOutstandingSalesUseCase,
)


@dataclass(frozen=True)
class ReceivableInvoice:
    sale_id: uuid.UUID
    invoice_number: str
    invoice_date: date
    due_date: date | None
    outstanding: Decimal
    days_overdue: int


@dataclass(frozen=True)
class CustomerReceivable:
    """What one customer owes (customer_id is None for sales with no customer attached)."""

    customer_id: uuid.UUID | None
    outstanding: Decimal
    invoices: list[ReceivableInvoice]

    @property
    def days_overdue(self) -> int:
        return max((i.days_overdue for i in self.invoices), default=0)


@dataclass(frozen=True)
class GetReceivablesQuery:
    business_id: uuid.UUID
    today: date


class GetReceivablesUseCase:
    """Who owes the business money (the udhaar list): unpaid and part-paid sales grouped by customer, the
    largest balance first.
    """

    def __init__(self, uow: SalesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: GetReceivablesQuery) -> list[CustomerReceivable]:
        sales = await ListOutstandingSalesUseCase(self._uow).execute(
            ListOutstandingSalesQuery(business_id=query.business_id)
        )
        by_customer: dict[uuid.UUID | None, list[ReceivableInvoice]] = {}
        for sale in sales:
            due = sale.due_date
            overdue = (query.today - due).days if due and due < query.today else 0
            by_customer.setdefault(sale.customer_id, []).append(
                ReceivableInvoice(
                    sale_id=sale.id,
                    invoice_number=sale.invoice_number,
                    invoice_date=sale.invoice_date,
                    due_date=sale.due_date,
                    outstanding=sale.outstanding_amount.amount,
                    days_overdue=overdue,
                )
            )
        groups = [
            CustomerReceivable(
                customer_id=customer_id,
                outstanding=sum((i.outstanding for i in invoices), Decimal("0")),
                invoices=sorted(invoices, key=lambda i: i.invoice_date),
            )
            for customer_id, invoices in by_customer.items()
        ]
        return sorted(groups, key=lambda g: g.outstanding, reverse=True)
