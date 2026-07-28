import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.expenses.application.commands.create_expense import CreateExpenseCommand, CreateExpenseUseCase
from app.expenses.application.commands.update_expense import UpdateExpenseCommand, UpdateExpenseUseCase
from app.expenses.application.commands.void_expense import VoidExpenseCommand, VoidExpenseUseCase
from app.expenses.application.queries.get_expense import GetExpenseQuery, GetExpenseUseCase
from app.expenses.application.queries.list_expenses import ListExpensesQuery, ListExpensesUseCase
from app.expenses.domain.exceptions import ExpenseNotFoundException
from app.expenses.domain.value_objects import ExpenseStatus, PaymentMethod
from app.shared.application.pagination import PageRequest
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


def make_create_command(business_id: uuid.UUID, **overrides) -> CreateExpenseCommand:
    defaults = dict(
        business_id=business_id,
        expense_date=date(2026, 1, 1),
        category="Office Supplies",
        description="Printer paper",
        amount=Decimal("50"),
        payment_method=PaymentMethod.CARD,
    )
    defaults.update(overrides)
    return CreateExpenseCommand(**defaults)


async def test_create_and_get_expense() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    created = await CreateExpenseUseCase(uow).execute(make_create_command(business_id))

    fetched = await GetExpenseUseCase(uow).execute(
        GetExpenseQuery(business_id=business_id, expense_id=created.id)
    )
    assert fetched.category == "Office Supplies"
    assert fetched.total_amount.amount == Decimal("50.00")


async def test_get_expense_from_wrong_business_raises() -> None:
    uow = FakeUnitOfWork()
    expense = await CreateExpenseUseCase(uow).execute(make_create_command(uuid.uuid4()))

    with pytest.raises(ExpenseNotFoundException):
        await GetExpenseUseCase(uow).execute(
            GetExpenseQuery(business_id=uuid.uuid4(), expense_id=expense.id)
        )


async def test_list_expenses_is_scoped_per_business() -> None:
    uow = FakeUnitOfWork()
    business_a = uuid.uuid4()
    business_b = uuid.uuid4()
    await CreateExpenseUseCase(uow).execute(make_create_command(business_a, category="A-cat"))
    await CreateExpenseUseCase(uow).execute(make_create_command(business_b, category="B-cat"))

    page = await ListExpensesUseCase(uow).execute(
        ListExpensesQuery(business_id=business_a, page=PageRequest())
    )

    assert page.total == 1
    assert page.items[0].category == "A-cat"


async def test_update_expense() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    expense = await CreateExpenseUseCase(uow).execute(make_create_command(business_id))

    updated = await UpdateExpenseUseCase(uow).execute(
        UpdateExpenseCommand(business_id=business_id, expense_id=expense.id, category="Utilities")
    )

    assert updated.category == "Utilities"


async def test_void_expense_use_case() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    expense = await CreateExpenseUseCase(uow).execute(make_create_command(business_id))

    voided = await VoidExpenseUseCase(uow).execute(
        VoidExpenseCommand(business_id=business_id, expense_id=expense.id)
    )

    assert voided.status == ExpenseStatus.VOID
