import uuid
from decimal import Decimal

import pytest

from app.invoices.domain.entities import Invoice
from app.invoices.domain.exceptions import EmptyInvoiceException, InvalidInvoiceStateTransitionException
from app.invoices.domain.value_objects import InvoiceLineItem, InvoiceStatus
from app.shared.domain.value_objects import Money


def make_line_item(line_number: int = 1) -> InvoiceLineItem:
    return InvoiceLineItem(
        line_number=line_number,
        description="Widgets",
        quantity=Decimal("2"),
        unit_price=Money(amount=Decimal("10.00")),
    )


def make_invoice() -> Invoice:
    invoice = Invoice.submit(
        invoice_number="INV-001",
        vendor_id=uuid.uuid4(),
        po_id=uuid.uuid4(),
        line_items=[make_line_item()],
    )
    invoice.pull_domain_events()
    return invoice


def test_submit_requires_line_items() -> None:
    with pytest.raises(EmptyInvoiceException):
        Invoice.submit(invoice_number="INV-002", vendor_id=uuid.uuid4(), po_id=uuid.uuid4(), line_items=[])


def test_submit_records_event_with_status_submitted() -> None:
    invoice = Invoice.submit(
        invoice_number="INV-001", vendor_id=uuid.uuid4(), po_id=uuid.uuid4(), line_items=[make_line_item()]
    )

    assert invoice.status == InvoiceStatus.SUBMITTED
    events = invoice.pull_domain_events()
    assert [e.event_type for e in events] == ["InvoiceSubmitted"]


def test_full_happy_path_state_machine() -> None:
    invoice = make_invoice()

    invoice.mark_matched()
    assert invoice.status == InvoiceStatus.MATCHED
    assert [e.event_type for e in invoice.pull_domain_events()] == ["InvoiceMatched"]

    invoice.mark_pending_approval()
    assert invoice.status == InvoiceStatus.PENDING_APPROVAL

    invoice.mark_approved()
    assert invoice.status == InvoiceStatus.APPROVED
    assert [e.event_type for e in invoice.pull_domain_events()] == ["InvoiceApproved"]


def test_rejection_path() -> None:
    invoice = make_invoice()
    invoice.mark_matched()
    invoice.mark_pending_approval()
    invoice.pull_domain_events()

    invoice.mark_rejected("Amount exceeds delegated authority")

    assert invoice.status == InvoiceStatus.REJECTED
    events = invoice.pull_domain_events()
    assert events[0].reason == "Amount exceeds delegated authority"


def test_match_exception_records_discrepancies() -> None:
    invoice = make_invoice()

    invoice.mark_match_exception(["Line 1: quantity mismatch"])

    assert invoice.status == InvoiceStatus.MATCH_EXCEPTION
    assert invoice.match_discrepancies == ["Line 1: quantity mismatch"]


def test_cannot_approve_before_matching() -> None:
    invoice = make_invoice()

    with pytest.raises(InvalidInvoiceStateTransitionException):
        invoice.mark_pending_approval()


def test_cannot_mark_matched_twice() -> None:
    invoice = make_invoice()
    invoice.mark_matched()

    with pytest.raises(InvalidInvoiceStateTransitionException):
        invoice.mark_matched()


def test_total_amount_sums_line_items() -> None:
    invoice = Invoice.submit(
        invoice_number="INV-003",
        vendor_id=uuid.uuid4(),
        po_id=uuid.uuid4(),
        line_items=[make_line_item(1), make_line_item(2)],
    )

    assert invoice.total_amount.amount == Decimal("40.00")
