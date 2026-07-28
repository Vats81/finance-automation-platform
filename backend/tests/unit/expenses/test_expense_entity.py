import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.expenses.domain.entities import Expense
from app.expenses.domain.exceptions import ExpenseAlreadyVoidException
from app.expenses.domain.value_objects import ExpenseStatus, PaymentMethod
from app.shared.domain.value_objects import Money


def make_expense(**overrides) -> Expense:
    defaults = dict(
        business_id=uuid.uuid4(),
        expense_date=date(2026, 1, 1),
        category="Office Supplies",
        description="Printer paper",
        amount=Money(amount=Decimal("50")),
        payment_method=PaymentMethod.CARD,
    )
    defaults.update(overrides)
    expense = Expense.create(**defaults)
    expense.pull_domain_events()
    return expense


def test_create_records_event_and_defaults_to_recorded() -> None:
    expense = Expense.create(
        business_id=uuid.uuid4(),
        expense_date=date(2026, 1, 1),
        category="Office Supplies",
        description="Printer paper",
        amount=Money(amount=Decimal("50")),
        payment_method=PaymentMethod.CARD,
    )

    assert expense.status == ExpenseStatus.RECORDED
    assert expense.total_amount == Money(amount=Decimal("50"))
    events = expense.pull_domain_events()
    assert [e.event_type for e in events] == ["ExpenseRecorded"]


def test_total_amount_includes_tax() -> None:
    expense = make_expense(amount=Money(amount=Decimal("50")), tax=Money(amount=Decimal("5")))
    assert expense.total_amount == Money(amount=Decimal("55"))


def test_update_details_only_records_event_when_something_changed() -> None:
    expense = make_expense()

    expense.update_details(category="Office Supplies")  # unchanged
    assert expense.pull_domain_events() == []

    expense.update_details(category="Utilities", is_recurring=True)
    events = expense.pull_domain_events()
    assert len(events) == 1
    assert set(events[0].changed_fields) == {"category", "is_recurring"}


def test_void_prevents_double_void() -> None:
    expense = make_expense()

    expense.void()
    assert expense.status == ExpenseStatus.VOID
    events = expense.pull_domain_events()
    assert [e.event_type for e in events] == ["ExpenseVoided"]

    with pytest.raises(ExpenseAlreadyVoidException):
        expense.void()
