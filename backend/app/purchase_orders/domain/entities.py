import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.purchase_orders.domain.events import (
    PurchaseOrderCancelled,
    PurchaseOrderClosed,
    PurchaseOrderCreated,
)
from app.purchase_orders.domain.exceptions import EmptyPurchaseOrderException, PurchaseOrderNotOpenException
from app.purchase_orders.domain.value_objects import PurchaseOrderLineItem, PurchaseOrderStatus
from app.shared.domain.aggregate_root import AggregateRoot
from app.shared.domain.value_objects import Money


class PurchaseOrder(AggregateRoot):
    """Own aggregate; referenced by Invoice only by id (`po_id`) — Invoice
    never loads or mutates a PurchaseOrder directly. 2-way matching
    (invoices/domain/matching/two_way_match.py) reads a PurchaseOrder's line
    items via IPurchaseOrderRepository, compares against submitted invoice
    line items, and raises MatchExceptionRaised if they diverge; it never
    calls back into PurchaseOrder to mutate it.
    """

    def __init__(
        self,
        *,
        entity_id: uuid.UUID | None = None,
        po_number: str,
        vendor_id: uuid.UUID,
        line_items: list[PurchaseOrderLineItem],
        status: PurchaseOrderStatus = PurchaseOrderStatus.OPEN,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.po_number = po_number
        self.vendor_id = vendor_id
        self.line_items = line_items
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)

    @classmethod
    def create(
        cls, *, vendor_id: uuid.UUID, line_items: list[PurchaseOrderLineItem]
    ) -> "PurchaseOrder":
        if not line_items:
            raise EmptyPurchaseOrderException("A purchase order requires at least one line item")

        po = cls(po_number=cls._generate_po_number(), vendor_id=vendor_id, line_items=line_items)
        po._record_event(
            PurchaseOrderCreated(
                aggregate_id=po.id,
                po_number=po.po_number,
                vendor_id=str(vendor_id),
                total_amount_cents=po.total_amount.cents,
            )
        )
        return po

    @staticmethod
    def _generate_po_number() -> str:
        return f"PO-{uuid.uuid4().hex[:8].upper()}"

    @property
    def total_amount(self) -> Money:
        total = Money(amount=Decimal("0"))
        for item in self.line_items:
            total = total + item.line_total
        return total

    def get_line(self, line_number: int) -> PurchaseOrderLineItem | None:
        return next((item for item in self.line_items if item.line_number == line_number), None)

    def close(self) -> None:
        if self.status != PurchaseOrderStatus.OPEN:
            raise PurchaseOrderNotOpenException(f"PurchaseOrder {self.id} is not open")
        self.status = PurchaseOrderStatus.CLOSED
        self._record_event(PurchaseOrderClosed(aggregate_id=self.id, po_number=self.po_number))

    def cancel(self) -> None:
        if self.status != PurchaseOrderStatus.OPEN:
            raise PurchaseOrderNotOpenException(f"PurchaseOrder {self.id} is not open")
        self.status = PurchaseOrderStatus.CANCELLED
        self._record_event(PurchaseOrderCancelled(aggregate_id=self.id, po_number=self.po_number))

    @property
    def is_open(self) -> bool:
        return self.status == PurchaseOrderStatus.OPEN
