import uuid

from app.data_import.application.import_vendors import ImportVendorsUseCase
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

MAPPING = {
    "legal_name": "Legal Name",
    "contact_email": "Email",
    "tax_id": "Tax ID",
    "street": "Street",
    "city": "City",
    "state": "State",
    "postal_code": "Zip",
}

VALID_ROW = {
    "Legal Name": "Acme Supplies",
    "Email": "ap@acme.example",
    "Tax ID": "12-3456789",
    "Street": "1 Main St",
    "City": "Springfield",
    "State": "IL",
    "Zip": "62701",
}


async def test_import_vendors_creates_valid_rows() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    summary = await ImportVendorsUseCase(uow).execute(
        business_id=business_id, rows=[VALID_ROW], column_mapping=MAPPING
    )

    assert summary.total_rows == 1
    assert summary.created == 1
    assert summary.skipped_duplicates == 0
    assert summary.errors == []
    vendors, total = await uow.vendors.list_for_business(business_id)
    assert total == 1
    assert vendors[0].legal_name == "Acme Supplies"


async def test_import_vendors_skips_duplicates_by_legal_name() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    duplicate_row = dict(VALID_ROW, **{"Legal Name": "acme supplies", "Tax ID": "99-9999999"})

    summary = await ImportVendorsUseCase(uow).execute(
        business_id=business_id, rows=[VALID_ROW, duplicate_row], column_mapping=MAPPING
    )

    assert summary.created == 1
    assert summary.skipped_duplicates == 1


async def test_import_vendors_reports_missing_required_field() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    incomplete_row = dict(VALID_ROW)
    incomplete_row["Tax ID"] = ""

    summary = await ImportVendorsUseCase(uow).execute(
        business_id=business_id, rows=[incomplete_row], column_mapping=MAPPING
    )

    assert summary.created == 0
    assert len(summary.errors) == 1
    assert summary.errors[0].row_number == 1
    assert "tax_id" in summary.errors[0].message


async def test_import_vendors_remaps_columns() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    row = {
        "Name": "Acme Supplies",
        "Contact": "ap@acme.example",
        "TIN": "12-3456789",
        "Addr1": "1 Main St",
        "Town": "Springfield",
        "Region": "IL",
        "Postcode": "62701",
    }
    mapping = {
        "legal_name": "Name",
        "contact_email": "Contact",
        "tax_id": "TIN",
        "street": "Addr1",
        "city": "Town",
        "state": "Region",
        "postal_code": "Postcode",
    }

    summary = await ImportVendorsUseCase(uow).execute(
        business_id=business_id, rows=[row], column_mapping=mapping
    )

    assert summary.created == 1
    vendors, _ = await uow.vendors.list_for_business(business_id)
    assert vendors[0].legal_name == "Acme Supplies"
