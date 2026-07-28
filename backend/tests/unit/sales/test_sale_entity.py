import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.sales.domain.entities import Sale
from app.sales.domain.exceptions import (
    EmptySaleException,
    PaymentExceedsOutstandingException,
    SaleAlreadyVoidException,
)
from app.sales.domain.value_objects import SaleLineItem, SalePaymentStatus, SaleStatus
from app.shared.domain.value_objects import Money


def make_line_items() -> list[SaleLineItem]:
    return [
        SaleLineItem(
            line_number=1,
            description="Widget",
            quantity=Decimal("2"),
            unit_price=Money(amount=Decimal("50")),
        ),
    ]


def make_sale(**overrides) -> Sale:
    defaults = dict(
        business_id=uuid.uuid4(),
        invoice_number="INV-001",
        customer_id=None,
        invoice_date=date(2026, 1, 1),
        due_date=None,
        line_items=make_line_items(),
    )
    defaults.update(overrides)
    sale = Sale.create(**defaults)
    sale.pull_domain_events()
    return sale


def test_create_with_no_line_items_raises() -> None:
    with pytest.raises(EmptySaleException):
        Sale.create(
            business_id=uuid.uuid4(),
            invoice_number="INV-001",
            customer_id=None,
            invoice_date=date(2026, 1, 1),
            due_date=None,
            line_items=[],
        )


def test_create_records_event_and_computes_totals() -> None:
    sale = Sale.create(
        business_id=uuid.uuid4(),
        invoice_number="INV-001",
        customer_id=None,
        invoice_date=date(2026, 1, 1),
        due_date=None,
        line_items=make_line_items(),
    )

    assert sale.subtotal == Money(amount=Decimal("100"))
    assert sale.total_amount == Money(amount=Decimal("100"))
    assert sale.payment_status == SalePaymentStatus.UNPAID
    events = sale.pull_domain_events()
    assert [e.event_type for e in events] == ["SaleRecorded"]


def test_total_amount_accounts_for_discount_and_tax() -> None:
    sale = make_sale(discount=Money(amount=Decimal("10")), tax=Money(amount=Decimal("5")))

    assert sale.total_amount == Money(amount=Decimal("95"))


def test_record_payment_updates_status_progressively() -> None:
    sale = make_sale()

    sale.record_payment(Money(amount=Decimal("40")))
    assert sale.payment_status == SalePaymentStatus.PARTIALLY_PAID
    assert sale.outstanding_amount == Money(amount=Decimal("60"))
    events = sale.pull_domain_events()
    assert [e.event_type for e in events] == ["SalePaymentRecorded"]

    sale.record_payment(Money(amount=Decimal("60")))
    assert sale.payment_status == SalePaymentStatus.PAID
    assert sale.outstanding_amount == Money(amount=Decimal("0"))


def test_record_payment_exceeding_outstanding_raises() -> None:
    sale = make_sale()

    with pytest.raises(PaymentExceedsOutstandingException):
        sale.record_payment(Money(amount=Decimal("101")))


def test_void_prevents_further_payments_and_double_void() -> None:
    sale = make_sale()

    sale.void()
    assert sale.status == SaleStatus.VOID
    events = sale.pull_domain_events()
    assert [e.event_type for e in events] == ["SaleVoided"]

    with pytest.raises(SaleAlreadyVoidException):
        sale.void()

    with pytest.raises(SaleAlreadyVoidException):
        sale.record_payment(Money(amount=Decimal("1")))
