import uuid
from decimal import Decimal

from app.invoices.domain.entities import Invoice
from app.invoices.domain.matching.two_way_match import TwoWayMatchService
from app.invoices.domain.value_objects import InvoiceLineItem
from app.purchase_orders.domain.entities import PurchaseOrder
from app.purchase_orders.domain.value_objects import PurchaseOrderLineItem
from app.shared.domain.value_objects import Money


def make_po(vendor_id: uuid.UUID, quantity: str = "2", unit_price: str = "10.00") -> PurchaseOrder:
    return PurchaseOrder.create(
        vendor_id=vendor_id,
        line_items=[
            PurchaseOrderLineItem(
                line_number=1,
                description="Widgets",
                quantity=Decimal(quantity),
                unit_price=Money(amount=Decimal(unit_price)),
            )
        ],
    )


def make_invoice(
    vendor_id: uuid.UUID, po_id: uuid.UUID, quantity: str = "2", unit_price: str = "10.00"
) -> Invoice:
    return Invoice.submit(
        invoice_number="INV-001",
        vendor_id=vendor_id,
        po_id=po_id,
        line_items=[
            InvoiceLineItem(
                line_number=1,
                description="Widgets",
                quantity=Decimal(quantity),
                unit_price=Money(amount=Decimal(unit_price)),
            )
        ],
    )


def test_matching_invoice_and_po_produces_no_discrepancies() -> None:
    vendor_id = uuid.uuid4()
    po = make_po(vendor_id)
    invoice = make_invoice(vendor_id, po.id)

    result = TwoWayMatchService.match(invoice, po)

    assert result.is_matched is True
    assert result.discrepancies == []


def test_quantity_mismatch_is_a_discrepancy() -> None:
    vendor_id = uuid.uuid4()
    po = make_po(vendor_id, quantity="2")
    invoice = make_invoice(vendor_id, po.id, quantity="3")

    result = TwoWayMatchService.match(invoice, po)

    assert result.is_matched is False
    assert any("quantity" in d for d in result.discrepancies)


def test_unit_price_mismatch_is_a_discrepancy() -> None:
    vendor_id = uuid.uuid4()
    po = make_po(vendor_id, unit_price="10.00")
    invoice = make_invoice(vendor_id, po.id, unit_price="12.00")

    result = TwoWayMatchService.match(invoice, po)

    assert result.is_matched is False
    assert any("unit price" in d for d in result.discrepancies)


def test_vendor_mismatch_is_a_discrepancy() -> None:
    po = make_po(uuid.uuid4())
    invoice = make_invoice(uuid.uuid4(), po.id)  # different vendor_id

    result = TwoWayMatchService.match(invoice, po)

    assert result.is_matched is False
    assert any("vendor" in d for d in result.discrepancies)


def test_invoice_line_with_no_matching_po_line_is_a_discrepancy() -> None:
    vendor_id = uuid.uuid4()
    po = make_po(vendor_id)
    invoice = Invoice.submit(
        invoice_number="INV-002",
        vendor_id=vendor_id,
        po_id=po.id,
        line_items=[
            InvoiceLineItem(
                line_number=99,
                description="Unrelated line",
                quantity=Decimal("1"),
                unit_price=Money(amount=Decimal("5.00")),
            )
        ],
    )

    result = TwoWayMatchService.match(invoice, po)

    assert result.is_matched is False
    assert any("no matching PO line" in d for d in result.discrepancies)
