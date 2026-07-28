import enum
from dataclasses import dataclass
from decimal import Decimal

from app.shared.domain.base_value_object import ValueObject
from app.shared.domain.exceptions import ValidationException
from app.shared.domain.value_objects import Money


class PurchaseOrderStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class PurchaseOrderLineItem(ValueObject):
    """Modeled as a value object (not a child entity) because line items on
    a PO have no independent identity or lifecycle outside the PO itself —
    they are fully replaced/recreated on edit rather than mutated in place.
    A stable `line_number` (not a UUID) is what invoices/domain/matching/
    references when matching against a specific PO line.
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
