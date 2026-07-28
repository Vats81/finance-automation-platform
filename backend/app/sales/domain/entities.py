import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from app.sales.domain.events import SalePaymentRecorded, SaleRecorded, SaleVoided
from app.sales.domain.exceptions import (
    EmptySaleException,
    PaymentExceedsOutstandingException,
    SaleAlreadyVoidException,
)
from app.sales.domain.value_objects import SaleLineItem, SalePaymentStatus, SaleStatus
from app.shared.domain.aggregate_root import AggregateRoot
from app.shared.domain.value_objects import Money


class Sale(AggregateRoot):
    """A recorded sales transaction. References Customer only by id (never
    loads/mutates it — same reasoning as Invoice referencing Vendor/PO by id
    only). Own aggregate; no approval workflow in this slice (unlike
    Invoice), since the spec's Sales Management module doesn't call for one.

    total_amount/outstanding_amount/payment_status are computed, never
    stored — see the properties below — so they can never drift out of
    sync with line_items/discount/tax/amount_received.
    """

    def __init__(
        self,
        *,
        entity_id: uuid.UUID | None = None,
        business_id: uuid.UUID,
        invoice_number: str,
        customer_id: uuid.UUID | None = None,
        invoice_date: date,
        due_date: date | None = None,
        line_items: list[SaleLineItem],
        discount: Money | None = None,
        tax: Money | None = None,
        amount_received: Money | None = None,
        notes: str | None = None,
        status: SaleStatus = SaleStatus.RECORDED,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.business_id = business_id
        self.invoice_number = invoice_number
        self.customer_id = customer_id
        self.invoice_date = invoice_date
        self.due_date = due_date
        self.line_items = line_items
        self.discount = discount or Money(amount=Decimal("0"))
        self.tax = tax or Money(amount=Decimal("0"))
        self.amount_received = amount_received or Money(amount=Decimal("0"))
        self.notes = notes
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)

    @classmethod
    def create(
        cls,
        *,
        business_id: uuid.UUID,
        invoice_number: str,
        customer_id: uuid.UUID | None,
        invoice_date: date,
        due_date: date | None,
        line_items: list[SaleLineItem],
        discount: Money | None = None,
        tax: Money | None = None,
        notes: str | None = None,
    ) -> "Sale":
        if not line_items:
            raise EmptySaleException("A sale requires at least one line item")

        sale = cls(
            business_id=business_id,
            invoice_number=invoice_number,
            customer_id=customer_id,
            invoice_date=invoice_date,
            due_date=due_date,
            line_items=line_items,
            discount=discount,
            tax=tax,
            notes=notes,
        )
        sale._record_event(
            SaleRecorded(
                aggregate_id=sale.id,
                business_id=str(business_id),
                invoice_number=invoice_number,
                total_amount_cents=sale.total_amount.cents,
            )
        )
        return sale

    @property
    def subtotal(self) -> Money:
        total = Money(amount=Decimal("0"))
        for item in self.line_items:
            total = total + item.line_total
        return total

    @property
    def total_amount(self) -> Money:
        return self.subtotal - self.discount + self.tax

    @property
    def outstanding_amount(self) -> Money:
        return self.total_amount - self.amount_received

    @property
    def payment_status(self) -> SalePaymentStatus:
        if self.amount_received.cents <= 0:
            return SalePaymentStatus.UNPAID
        if self.amount_received.cents >= self.total_amount.cents:
            return SalePaymentStatus.PAID
        return SalePaymentStatus.PARTIALLY_PAID

    def record_payment(self, amount: Money) -> None:
        if self.status == SaleStatus.VOID:
            raise SaleAlreadyVoidException(f"Sale {self.id} is void and cannot receive payments")

        new_received = self.amount_received + amount
        if new_received.cents > self.total_amount.cents:
            raise PaymentExceedsOutstandingException(
                f"Payment of {amount} would exceed the outstanding balance on sale {self.id}"
            )

        self.amount_received = new_received
        self._record_event(
            SalePaymentRecorded(
                aggregate_id=self.id,
                amount_cents=amount.cents,
                amount_received_cents=self.amount_received.cents,
            )
        )

    def void(self) -> None:
        if self.status == SaleStatus.VOID:
            raise SaleAlreadyVoidException(f"Sale {self.id} is already void")

        self.status = SaleStatus.VOID
        self._record_event(SaleVoided(aggregate_id=self.id, invoice_number=self.invoice_number))
