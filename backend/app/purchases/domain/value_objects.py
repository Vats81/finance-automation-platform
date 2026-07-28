import enum
import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.shared.domain.base_value_object import ValueObject
from app.shared.domain.exceptions import ValidationException
from app.shared.domain.value_objects import Money


class PurchaseStatus(str, enum.Enum):
    RECORDED = "recorded"
    VOID = "void"


class PurchasePaymentStatus(str, enum.Enum):
    """Derived, never stored directly (see Purchase.payment_status) — so it
    can never drift out of sync with amount_paid/total_amount.
    """

    UNPAID = "unpaid"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"


@dataclass(frozen=True)
class PurchaseLineItem(ValueObject):
    """Identical shape/validation to sales/domain/value_objects.py's
    SaleLineItem plus an optional product_id — a data-only link to
    inventory.Product in this slice (see Slice 5 plan: no automatic stock
    adjustment yet). Deliberately duplicated per the codebase's own
    bounded-context rule rather than imported from sales/invoices/purchase_orders.
    """

    line_number: int
    description: str
    quantity: Decimal
    unit_cost: Money
    product_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValidationException("Line item quantity must be positive")
        if not self.description:
            raise ValidationException("Line item description is required")

    @property
    def line_total(self) -> Money:
        return self.unit_cost * self.quantity
