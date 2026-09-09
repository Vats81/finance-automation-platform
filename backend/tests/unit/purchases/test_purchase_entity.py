import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.purchases.domain.entities import Purchase
from app.purchases.domain.exceptions import (
    EmptyPurchaseException,
    PurchaseAlreadyVoidException,
    PurchasePaymentExceedsOutstandingException,
)
from app.purchases.domain.value_objects import PurchaseLineItem, PurchasePaymentStatus, PurchaseStatus
from app.shared.domain.value_objects import Money


def make_line_items() -> list[PurchaseLineItem]:
    return [
        PurchaseLineItem(
            line_number=1,
            description="Raw materials",
            quantity=Decimal("10"),
            unit_cost=Money(amount=Decimal("5")),
        ),
    ]


def make_purchase(**overrides) -> Purchase:
    defaults = dict(
        business_id=uuid.uuid4(),
        purchase_number="PO-001",
        vendor_id=uuid.uuid4(),
        purchase_date=date(2026, 1, 1),
        due_date=None,
        line_items=make_line_items(),
    )
    defaults.update(overrides)
    purchase = Purchase.create(**defaults)
    purchase.pull_domain_events()
    return purchase


def test_create_with_no_line_items_raises() -> None:
    with pytest.raises(EmptyPurchaseException):
        Purchase.create(
            business_id=uuid.uuid4(),
            purchase_number="PO-001",
            vendor_id=uuid.uuid4(),
            purchase_date=date(2026, 1, 1),
            due_date=None,
            line_items=[],
        )


def test_create_records_event_and_computes_totals() -> None:
    purchase = Purchase.create(
        business_id=uuid.uuid4(),
        purchase_number="PO-001",
        vendor_id=uuid.uuid4(),
        purchase_date=date(2026, 1, 1),
        due_date=None,
        line_items=make_line_items(),
    )

    assert purchase.subtotal == Money(amount=Decimal("50"))
    assert purchase.total_amount == Money(amount=Decimal("50"))
    assert purchase.payment_status == PurchasePaymentStatus.UNPAID
    events = purchase.pull_domain_events()
    assert [e.event_type for e in events] == ["PurchaseRecorded"]


def test_total_amount_accounts_for_tax() -> None:
    purchase = make_purchase(tax=Money(amount=Decimal("5")))
    assert purchase.total_amount == Money(amount=Decimal("55"))


def test_record_payment_updates_status_progressively() -> None:
    purchase = make_purchase()

    purchase.record_payment(Money(amount=Decimal("20")))
    assert purchase.payment_status == PurchasePaymentStatus.PARTIALLY_PAID
    assert purchase.outstanding_amount == Money(amount=Decimal("30"))
    events = purchase.pull_domain_events()
    assert [e.event_type for e in events] == ["PurchasePaymentRecorded"]

    purchase.record_payment(Money(amount=Decimal("30")))
    assert purchase.payment_status == PurchasePaymentStatus.PAID
    assert purchase.outstanding_amount == Money(amount=Decimal("0"))


def test_record_payment_exceeding_outstanding_raises() -> None:
    purchase = make_purchase()

    with pytest.raises(PurchasePaymentExceedsOutstandingException):
        purchase.record_payment(Money(amount=Decimal("51")))


def test_void_prevents_further_payments_and_double_void() -> None:
    purchase = make_purchase()

    purchase.void()
    assert purchase.status == PurchaseStatus.VOID
    events = purchase.pull_domain_events()
    assert [e.event_type for e in events] == ["PurchaseVoided"]

    with pytest.raises(PurchaseAlreadyVoidException):
        purchase.void()

    with pytest.raises(PurchaseAlreadyVoidException):
        purchase.record_payment(Money(amount=Decimal("1")))


def test_update_details_changes_fields_and_records_event() -> None:
    purchase = make_purchase()
    new_line_items = [
        PurchaseLineItem(
            line_number=1,
            description="Different materials",
            quantity=Decimal("2"),
            unit_cost=Money(amount=Decimal("15")),
        )
    ]

    purchase.update_details(
        purchase_number="PO-002",
        vendor_id=purchase.vendor_id,
        purchase_date=purchase.purchase_date,
        due_date=purchase.due_date,
        line_items=new_line_items,
        tax=purchase.tax,
        notes="updated",
    )

    assert purchase.purchase_number == "PO-002"
    assert purchase.line_items == new_line_items
    assert purchase.notes == "updated"
    events = purchase.pull_domain_events()
    assert [e.event_type for e in events] == ["PurchaseDetailsUpdated"]
    assert set(events[0].changed_fields) == {"purchase_number", "line_items", "notes"}


def test_update_details_is_a_noop_when_nothing_changes() -> None:
    purchase = make_purchase()

    purchase.update_details(
        purchase_number=purchase.purchase_number,
        vendor_id=purchase.vendor_id,
        purchase_date=purchase.purchase_date,
        due_date=purchase.due_date,
        line_items=purchase.line_items,
        tax=purchase.tax,
        notes=purchase.notes,
    )

    assert purchase.pull_domain_events() == []


def test_update_details_on_void_purchase_raises() -> None:
    purchase = make_purchase()
    purchase.void()

    with pytest.raises(PurchaseAlreadyVoidException):
        purchase.update_details(
            purchase_number=purchase.purchase_number,
            vendor_id=purchase.vendor_id,
            purchase_date=purchase.purchase_date,
            due_date=purchase.due_date,
            line_items=purchase.line_items,
            tax=purchase.tax,
            notes="new notes",
        )


def test_update_details_that_would_leave_paid_exceeding_new_total_raises() -> None:
    purchase = make_purchase()
    purchase.record_payment(Money(amount=Decimal("50")))
    purchase.pull_domain_events()
    smaller_line_items = [
        PurchaseLineItem(
            line_number=1,
            description="Raw materials",
            quantity=Decimal("1"),
            unit_cost=Money(amount=Decimal("5")),
        )
    ]

    with pytest.raises(PurchasePaymentExceedsOutstandingException):
        purchase.update_details(
            purchase_number=purchase.purchase_number,
            vendor_id=purchase.vendor_id,
            purchase_date=purchase.purchase_date,
            due_date=purchase.due_date,
            line_items=smaller_line_items,
            tax=purchase.tax,
            notes=purchase.notes,
        )
