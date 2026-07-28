import uuid

from app.data_import.application.import_customers import ImportCustomersUseCase
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

MAPPING = {"name": "Customer Name", "phone": "Phone", "email": "Email"}


async def test_import_customers_creates_valid_rows() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    rows = [
        {"Customer Name": "Jane's Diner", "Phone": "555-0100", "Email": "jane@example.com"},
        {"Customer Name": "Bob's Cafe", "Phone": "555-0101", "Email": "bob@example.com"},
    ]

    summary = await ImportCustomersUseCase(uow).execute(
        business_id=business_id, rows=rows, column_mapping=MAPPING
    )

    assert summary.total_rows == 2
    assert summary.created == 2
    assert summary.skipped_duplicates == 0
    assert summary.errors == []
    customers, total = await uow.customers.list_for_business(business_id)
    assert total == 2


async def test_import_customers_skips_duplicates_by_name() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    rows = [
        {"Customer Name": "Jane's Diner", "Phone": "555-0100", "Email": "jane@example.com"},
        {"Customer Name": "jane's diner", "Phone": "555-9999", "Email": "other@example.com"},
    ]

    summary = await ImportCustomersUseCase(uow).execute(
        business_id=business_id, rows=rows, column_mapping=MAPPING
    )

    assert summary.created == 1
    assert summary.skipped_duplicates == 1


async def test_import_customers_reports_missing_required_field() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    rows = [{"Customer Name": "", "Phone": "555-0100", "Email": "jane@example.com"}]

    summary = await ImportCustomersUseCase(uow).execute(
        business_id=business_id, rows=rows, column_mapping=MAPPING
    )

    assert summary.created == 0
    assert len(summary.errors) == 1
    assert summary.errors[0].row_number == 1
    assert "name" in summary.errors[0].message


async def test_import_customers_remaps_columns() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    rows = [{"Full Name": "Jane's Diner", "Contact Phone": "555-0100"}]
    mapping = {"name": "Full Name", "phone": "Contact Phone"}

    summary = await ImportCustomersUseCase(uow).execute(
        business_id=business_id, rows=rows, column_mapping=mapping
    )

    assert summary.created == 1
    customers, _ = await uow.customers.list_for_business(business_id)
    assert customers[0].name == "Jane's Diner"
    assert customers[0].phone == "555-0100"
