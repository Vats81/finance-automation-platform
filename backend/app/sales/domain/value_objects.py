import enum
from dataclasses import dataclass
from decimal import Decimal

from app.shared.domain.base_value_object import ValueObject
from app.shared.domain.exceptions import ValidationException
from app.shared.domain.value_objects import Money


class SaleStatus(str, enum.Enum):
    RECORDED = "recorded"
    VOID = "void"


class SalePaymentStatus(str, enum.Enum):
    """Derived, never stored directly (see Sale.payment_status) — so it can
    never drift out of sync with amount_received/total_amount.
    """

    UNPAID = "unpaid"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"


@dataclass(frozen=True)
class SaleLineItem(ValueObject):
    """Identical shape/validation to invoices/domain/value_objects.py's
    InvoiceLineItem and purchase_orders/domain/value_objects.py's
    PurchaseOrderLineItem — deliberately duplicated per the codebase's own
    bounded-context rule rather than imported from either.
    """

    line_number: int
    description: str
    quantity: Decimal
    unit_price: Money

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValidationException("Line item quantity must be positive")
        if not self.description:
            raise ValidationException("Line item description is required")

    @property
    def line_total(self) -> Money:
        return self.unit_price * self.quantity
