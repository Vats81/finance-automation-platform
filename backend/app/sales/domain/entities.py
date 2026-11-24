import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from app.sales.domain.events import SaleDetailsUpdated, SalePaymentRecorded, SaleRecorded, SaleVoided
from app.sales.domain.exceptions import (
    EmptySaleException,
    PaymentExceedsOutstandingException,
    SaleAlreadyVoidException,
)
from app.sales.domain.value_objects import SaleLineItem, SalePaymentStatus, SaleStatus
from app.shared.domain.aggregate_root import AggregateRoot
from app.shared.domain.exceptions import ValidationException
from app.shared.domain.gst import clean_state_code
from app.shared.domain.value_objects import Money


@dataclass(frozen=True)
class GstGroup:
    """One GST rate on an invoice: the value it is charged on, and the tax."""

    rate: Decimal
    taxable_value: Money
    tax: Money


def compute_gst(line_items: list[SaleLineItem], discount: Money) -> list[GstGroup]:
    """GST per rate. The discount is shared out over the lines in proportion to their value, then the tax is
    worked out once per rate on the group's total (as a GST invoice's tax summary does).
    """
    subtotal = sum((i.line_total.amount for i in line_items), Decimal("0"))
    taxable_by_rate: dict[Decimal, Decimal] = {}
    for item in line_items:
        share = discount.amount * item.line_total.amount / subtotal if subtotal > 0 else Decimal("0")
        rate = item.gst_rate if item.gst_rate is not None else Decimal("0")
        taxable_by_rate[rate] = taxable_by_rate.get(rate, Decimal("0")) + item.line_total.amount - share
    groups = []
    for rate in sorted(taxable_by_rate):
        taxable = Money(amount=taxable_by_rate[rate])
        groups.append(
            GstGroup(rate=rate, taxable_value=taxable, tax=Money(amount=taxable.amount * rate / 100))
        )
    return groups


def _gst_tax(line_items: list[SaleLineItem], discount: Money, entered_tax: Money | None) -> Money | None:
    """The tax to store when the lines carry GST rates, or the entered tax when they do not."""
    if not any(item.gst_rate is not None for item in line_items):
        return entered_tax
    if entered_tax is not None and entered_tax.amount != 0:
        raise ValidationException(
            "GST is worked out from the rates on the lines, so do not also enter a tax amount."
        )
    return sum((g.tax for g in compute_gst(line_items, discount)), Money(amount=Decimal("0")))


def _check_adjustments(subtotal: Money, discount: Money, tax: Money) -> None:
    """A negative discount or tax, or a discount larger than the subtotal,
    produced negative sales (and a negative revenue figure on the dashboard).
    """
    if discount.amount < 0:
        raise ValidationException("Discount cannot be negative")
    if tax.amount < 0:
        raise ValidationException("Tax cannot be negative")
    if discount.amount > subtotal.amount:
        raise ValidationException("Discount cannot be larger than the sale subtotal")


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
        place_of_supply: str | None = None,
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
        # The state (GST code) the goods or services are supplied to; it decides CGST+SGST or IGST.
        self.place_of_supply = place_of_supply
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
        place_of_supply: str | None = None,
    ) -> "Sale":
        if not line_items:
            raise EmptySaleException("A sale requires at least one line item")
        tax = _gst_tax(line_items, discount or Money(amount=Decimal("0")), tax)
        if place_of_supply is not None:
            place_of_supply = clean_state_code(place_of_supply)
        _check_adjustments(
            sum((i.line_total for i in line_items), Money(amount=Decimal("0"))),
            discount or Money(amount=Decimal("0")),
            tax or Money(amount=Decimal("0")),
        )

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
            place_of_supply=place_of_supply,
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
    def gst_groups(self) -> list[GstGroup]:
        """Empty unless the lines carry GST rates."""
        if not any(item.gst_rate is not None for item in self.line_items):
            return []
        return compute_gst(self.line_items, self.discount)

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

    def update_details(
        self,
        *,
        invoice_number: str,
        customer_id: uuid.UUID | None,
        invoice_date: date,
        due_date: date | None,
        line_items: list[SaleLineItem],
        discount: Money,
        tax: Money,
        notes: str | None,
        place_of_supply: str | None = None,
    ) -> None:
        """Full-replacement edit — the frontend edit form always resends the
        complete new state rather than a sparse patch, so there's no
        None-means-'leave unchanged' ambiguity to resolve for a field like
        customer_id that's itself nullable (unlike Vendor/Customer's
        update_details, which only touches fields explicitly passed).
        Records one event only if something actually changed.
        """
        if self.status == SaleStatus.VOID:
            raise SaleAlreadyVoidException(f"Sale {self.id} is void and cannot be edited")
        if not line_items:
            raise EmptySaleException("A sale requires at least one line item")

        tax = _gst_tax(line_items, discount, tax) or Money(amount=Decimal("0"))
        if place_of_supply is not None:
            place_of_supply = clean_state_code(place_of_supply)
        new_subtotal = Money(amount=Decimal("0"))
        for item in line_items:
            new_subtotal = new_subtotal + item.line_total
        _check_adjustments(new_subtotal, discount, tax)
        new_total = new_subtotal - discount + tax
        if self.amount_received.cents > new_total.cents:
            raise PaymentExceedsOutstandingException(
                f"Editing sale {self.id} this way would make the amount already received "
                "exceed the new total"
            )

        changed: list[str] = []
        if invoice_number != self.invoice_number:
            self.invoice_number = invoice_number
            changed.append("invoice_number")
        if customer_id != self.customer_id:
            self.customer_id = customer_id
            changed.append("customer_id")
        if invoice_date != self.invoice_date:
            self.invoice_date = invoice_date
            changed.append("invoice_date")
        if due_date != self.due_date:
            self.due_date = due_date
            changed.append("due_date")
        if line_items != self.line_items:
            self.line_items = line_items
            changed.append("line_items")
        if discount != self.discount:
            self.discount = discount
            changed.append("discount")
        if tax != self.tax:
            self.tax = tax
            changed.append("tax")
        if notes != self.notes:
            self.notes = notes
            changed.append("notes")
        if place_of_supply != self.place_of_supply:
            self.place_of_supply = place_of_supply
            changed.append("place_of_supply")

        if changed:
            self._record_event(SaleDetailsUpdated(aggregate_id=self.id, changed_fields=changed))
