import uuid

from app.data_import.application.import_expenses import ImportExpensesUseCase
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

MAPPING = {
    "expense_date": "Date",
    "category": "Category",
    "description": "Description",
    "amount": "Amount",
    "payment_method": "Method",
    "is_recurring": "Recurring",
}

VALID_ROW = {
    "Date": "2026-01-15",
    "Category": "Office Supplies",
    "Description": "Printer paper",
    "Amount": "25.00",
    "Method": "cash",
    "Recurring": "no",
}


async def test_import_expenses_creates_valid_rows() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    summary = await ImportExpensesUseCase(uow).execute(
        business_id=business_id, rows=[VALID_ROW], column_mapping=MAPPING
    )

    assert summary.total_rows == 1
    assert summary.created == 1
    assert summary.skipped_duplicates == 0
    assert summary.errors == []
    expenses, total = await uow.expenses.list_for_business(business_id)
    assert total == 1
    assert expenses[0].description == "Printer paper"
    assert expenses[0].is_recurring is False


async def test_import_expenses_has_no_dedup_even_for_identical_rows() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    summary = await ImportExpensesUseCase(uow).execute(
        business_id=business_id, rows=[VALID_ROW, VALID_ROW], column_mapping=MAPPING
    )

    assert summary.created == 2
    assert summary.skipped_duplicates == 0


async def test_import_expenses_reports_missing_required_field() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    incomplete_row = dict(VALID_ROW)
    incomplete_row["Amount"] = ""

    summary = await ImportExpensesUseCase(uow).execute(
        business_id=business_id, rows=[incomplete_row], column_mapping=MAPPING
    )

    assert summary.created == 0
    assert len(summary.errors) == 1
    assert summary.errors[0].row_number == 1
    assert "amount" in summary.errors[0].message


async def test_import_expenses_reports_invalid_date() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    bad_row = dict(VALID_ROW, **{"Date": "not-a-date"})

    summary = await ImportExpensesUseCase(uow).execute(
        business_id=business_id, rows=[bad_row], column_mapping=MAPPING
    )

    assert summary.created == 0
    assert len(summary.errors) == 1
    assert summary.errors[0].row_number == 1


async def test_import_expenses_reports_invalid_payment_method() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    bad_row = dict(VALID_ROW, **{"Method": "bitcoin"})

    summary = await ImportExpensesUseCase(uow).execute(
        business_id=business_id, rows=[bad_row], column_mapping=MAPPING
    )

    assert summary.created == 0
    assert len(summary.errors) == 1


async def test_import_expenses_remaps_columns() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    row = {
        "When": "2026-01-15",
        "Type": "Office Supplies",
        "Notes1": "Printer paper",
        "Total": "25.00",
        "How Paid": "card",
    }
    mapping = {
        "expense_date": "When",
        "category": "Type",
        "description": "Notes1",
        "amount": "Total",
        "payment_method": "How Paid",
    }

    summary = await ImportExpensesUseCase(uow).execute(
        business_id=business_id, rows=[row], column_mapping=mapping
    )

    assert summary.created == 1
    expenses, _ = await uow.expenses.list_for_business(business_id)
    assert expenses[0].category == "Office Supplies"
