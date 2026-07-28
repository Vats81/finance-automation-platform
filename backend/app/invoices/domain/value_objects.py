import enum
from dataclasses import dataclass
from decimal import Decimal

from app.shared.domain.base_value_object import ValueObject
from app.shared.domain.exceptions import ValidationException
from app.shared.domain.value_objects import Money


class InvoiceStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    MATCHED = "matched"
    MATCH_EXCEPTION = "match_exception"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class InvoiceLineItem(ValueObject):
    """Value object, mirroring purchase_orders/domain/value_objects.py's
    PurchaseOrderLineItem — both are keyed by a stable `line_number` (not an
    identity) that invoices/domain/matching/two_way_match.py uses to pair an
    invoice line with its corresponding PO line. No independent lifecycle:
    edits replace the whole line_items list on the aggregate.
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
