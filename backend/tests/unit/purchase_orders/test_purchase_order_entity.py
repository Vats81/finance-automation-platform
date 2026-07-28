import uuid
from decimal import Decimal

import pytest

from app.purchase_orders.domain.entities import PurchaseOrder
from app.purchase_orders.domain.exceptions import EmptyPurchaseOrderException, PurchaseOrderNotOpenException
from app.purchase_orders.domain.value_objects import PurchaseOrderLineItem, PurchaseOrderStatus
from app.shared.domain.value_objects import Money


def make_line_item(
    line_number: int = 1, quantity: str = "2", unit_price: str = "10.00"
) -> PurchaseOrderLineItem:
    return PurchaseOrderLineItem(
        line_number=line_number,
        description="Widgets",
        quantity=Decimal(quantity),
        unit_price=Money(amount=Decimal(unit_price)),
    )


def test_create_requires_at_least_one_line_item() -> None:
    with pytest.raises(EmptyPurchaseOrderException):
        PurchaseOrder.create(vendor_id=uuid.uuid4(), line_items=[])


def test_create_generates_po_number_and_records_event() -> None:
    po = PurchaseOrder.create(vendor_id=uuid.uuid4(), line_items=[make_line_item()])

    assert po.po_number.startswith("PO-")
    assert po.status == PurchaseOrderStatus.OPEN
    events = po.pull_domain_events()
    assert [e.event_type for e in events] == ["PurchaseOrderCreated"]


def test_total_amount_sums_line_items() -> None:
    po = PurchaseOrder.create(
        vendor_id=uuid.uuid4(),
        line_items=[
            make_line_item(line_number=1, quantity="2", unit_price="10.00"),
            make_line_item(line_number=2, quantity="3", unit_price="5.00"),
        ],
    )

    assert po.total_amount.amount == Decimal("35.00")


def test_get_line_returns_matching_line_number() -> None:
    po = PurchaseOrder.create(vendor_id=uuid.uuid4(), line_items=[make_line_item(line_number=2)])

    assert po.get_line(2) is not None
    assert po.get_line(99) is None


def test_close_then_close_again_raises() -> None:
    po = PurchaseOrder.create(vendor_id=uuid.uuid4(), line_items=[make_line_item()])
    po.pull_domain_events()

    po.close()
    assert po.status == PurchaseOrderStatus.CLOSED

    with pytest.raises(PurchaseOrderNotOpenException):
        po.close()


def test_cancel_requires_open_status() -> None:
    po = PurchaseOrder.create(vendor_id=uuid.uuid4(), line_items=[make_line_item()])
    po.close()

    with pytest.raises(PurchaseOrderNotOpenException):
        po.cancel()
