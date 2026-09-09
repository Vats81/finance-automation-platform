import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from app.purchases.domain.events import (
    PurchaseDetailsUpdated,
    PurchasePaymentRecorded,
    PurchaseRecorded,
    PurchaseVoided,
)
from app.purchases.domain.exceptions import (
    EmptyPurchaseException,
    PurchaseAlreadyVoidException,
    PurchasePaymentExceedsOutstandingException,
)
from app.purchases.domain.value_objects import PurchaseLineItem, PurchasePaymentStatus, PurchaseStatus
from app.shared.domain.aggregate_root import AggregateRoot
from app.shared.domain.value_objects import Money


class Purchase(AggregateRoot):
    """A recorded purchase from a vendor — the AP-side mirror of `Sale`
    (sales/domain/entities.py). References Vendor (required — a purchase
    always has a supplier) and, per line item, an optional Product only by
    id; never loads/mutates either. No cross-context stock adjustment yet
    (see Slice 5 plan) — line items carry product_id purely as a data link.
    """

    def __init__(
        self,
        *,
        entity_id: uuid.UUID | None = None,
        business_id: uuid.UUID,
        purchase_number: str,
        vendor_id: uuid.UUID,
        purchase_date: date,
        due_date: date | None = None,
        line_items: list[PurchaseLineItem],
        tax: Money | None = None,
        amount_paid: Money | None = None,
        notes: str | None = None,
        status: PurchaseStatus = PurchaseStatus.RECORDED,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.business_id = business_id
        self.purchase_number = purchase_number
        self.vendor_id = vendor_id
        self.purchase_date = purchase_date
        self.due_date = due_date
        self.line_items = line_items
        self.tax = tax or Money(amount=Decimal("0"))
        self.amount_paid = amount_paid or Money(amount=Decimal("0"))
        self.notes = notes
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)

    @classmethod
    def create(
        cls,
        *,
        business_id: uuid.UUID,
        purchase_number: str,
        vendor_id: uuid.UUID,
        purchase_date: date,
        due_date: date | None,
        line_items: list[PurchaseLineItem],
        tax: Money | None = None,
        notes: str | None = None,
    ) -> "Purchase":
        if not line_items:
            raise EmptyPurchaseException("A purchase requires at least one line item")

        purchase = cls(
            business_id=business_id,
            purchase_number=purchase_number,
            vendor_id=vendor_id,
            purchase_date=purchase_date,
            due_date=due_date,
            line_items=line_items,
            tax=tax,
            notes=notes,
        )
        purchase._record_event(
            PurchaseRecorded(
                aggregate_id=purchase.id,
                business_id=str(business_id),
                purchase_number=purchase_number,
                vendor_id=str(vendor_id),
                total_amount_cents=purchase.total_amount.cents,
            )
        )
        return purchase

    @property
    def subtotal(self) -> Money:
        total = Money(amount=Decimal("0"))
        for item in self.line_items:
            total = total + item.line_total
        return total

    @property
    def total_amount(self) -> Money:
        return self.subtotal + self.tax

    @property
    def outstanding_amount(self) -> Money:
        return self.total_amount - self.amount_paid

    @property
    def payment_status(self) -> PurchasePaymentStatus:
        if self.amount_paid.cents <= 0:
            return PurchasePaymentStatus.UNPAID
        if self.amount_paid.cents >= self.total_amount.cents:
            return PurchasePaymentStatus.PAID
        return PurchasePaymentStatus.PARTIALLY_PAID

    def record_payment(self, amount: Money) -> None:
        if self.status == PurchaseStatus.VOID:
            raise PurchaseAlreadyVoidException(f"Purchase {self.id} is void and cannot receive payments")

        new_paid = self.amount_paid + amount
        if new_paid.cents > self.total_amount.cents:
            raise PurchasePaymentExceedsOutstandingException(
                f"Payment of {amount} would exceed the outstanding balance on purchase {self.id}"
            )

        self.amount_paid = new_paid
        self._record_event(
            PurchasePaymentRecorded(
                aggregate_id=self.id, amount_cents=amount.cents, amount_paid_cents=self.amount_paid.cents
            )
        )

    def void(self) -> None:
        if self.status == PurchaseStatus.VOID:
            raise PurchaseAlreadyVoidException(f"Purchase {self.id} is already void")

        self.status = PurchaseStatus.VOID
        self._record_event(PurchaseVoided(aggregate_id=self.id, purchase_number=self.purchase_number))

    def update_details(
        self,
        *,
        purchase_number: str,
        vendor_id: uuid.UUID,
        purchase_date: date,
        due_date: date | None,
        line_items: list[PurchaseLineItem],
        tax: Money,
        notes: str | None,
    ) -> None:
        """Full-replacement edit — see Sale.update_details' docstring for
        why this doesn't use the Vendor/Customer-style
        None-means-'leave unchanged' pattern.
        """
        if self.status == PurchaseStatus.VOID:
            raise PurchaseAlreadyVoidException(f"Purchase {self.id} is void and cannot be edited")
        if not line_items:
            raise EmptyPurchaseException("A purchase requires at least one line item")

        new_subtotal = Money(amount=Decimal("0"))
        for item in line_items:
            new_subtotal = new_subtotal + item.line_total
        new_total = new_subtotal + tax
        if self.amount_paid.cents > new_total.cents:
            raise PurchasePaymentExceedsOutstandingException(
                f"Editing purchase {self.id} this way would make the amount already paid "
                "exceed the new total"
            )

        changed: list[str] = []
        if purchase_number != self.purchase_number:
            self.purchase_number = purchase_number
            changed.append("purchase_number")
        if vendor_id != self.vendor_id:
            self.vendor_id = vendor_id
            changed.append("vendor_id")
        if purchase_date != self.purchase_date:
            self.purchase_date = purchase_date
            changed.append("purchase_date")
        if due_date != self.due_date:
            self.due_date = due_date
            changed.append("due_date")
        if line_items != self.line_items:
            self.line_items = line_items
            changed.append("line_items")
        if tax != self.tax:
            self.tax = tax
            changed.append("tax")
        if notes != self.notes:
            self.notes = notes
            changed.append("notes")

        if changed:
            self._record_event(PurchaseDetailsUpdated(aggregate_id=self.id, changed_fields=changed))
