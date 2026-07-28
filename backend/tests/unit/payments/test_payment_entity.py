import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.payments.domain.entities import Payment
from app.payments.domain.exceptions import InvalidPaymentStateTransitionException
from app.payments.domain.value_objects import PaymentStatus
from app.shared.domain.value_objects import Money


def make_payment() -> Payment:
    payment = Payment.schedule(
        invoice_id=uuid.uuid4(),
        vendor_id=uuid.uuid4(),
        amount=Money(amount=Decimal("500.00")),
        scheduled_date=datetime.now(timezone.utc) + timedelta(days=30),
    )
    payment.pull_domain_events()
    return payment


def test_schedule_records_payment_scheduled_event() -> None:
    payment = Payment.schedule(
        invoice_id=uuid.uuid4(),
        vendor_id=uuid.uuid4(),
        amount=Money(amount=Decimal("500.00")),
        scheduled_date=datetime.now(timezone.utc) + timedelta(days=30),
    )

    assert payment.status == PaymentStatus.SCHEDULED
    events = payment.pull_domain_events()
    assert [e.event_type for e in events] == ["PaymentScheduled"]
    assert events[0].amount_cents == 50000


def test_mark_paid_transitions_and_records_event() -> None:
    payment = make_payment()

    payment.mark_paid()

    assert payment.status == PaymentStatus.PAID
    events = payment.pull_domain_events()
    assert events[0].previous_status == "scheduled"
    assert events[0].new_status == "paid"


def test_cannot_mark_paid_twice() -> None:
    payment = make_payment()
    payment.mark_paid()

    with pytest.raises(InvalidPaymentStateTransitionException):
        payment.mark_paid()


def test_cancel_from_scheduled_succeeds() -> None:
    payment = make_payment()

    payment.cancel()

    assert payment.status == PaymentStatus.CANCELLED


def test_cannot_cancel_a_paid_payment() -> None:
    payment = make_payment()
    payment.mark_paid()

    with pytest.raises(InvalidPaymentStateTransitionException):
        payment.cancel()
