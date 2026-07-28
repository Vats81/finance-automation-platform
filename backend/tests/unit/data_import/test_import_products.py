import uuid

from app.data_import.application.import_products import ImportProductsUseCase
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

MAPPING = {
    "name": "Name",
    "sku": "SKU",
    "selling_price": "Selling Price",
    "purchase_cost": "Purchase Cost",
    "current_quantity": "Qty",
}

VALID_ROW = {
    "Name": "Widget",
    "SKU": "WID-001",
    "Selling Price": "19.99",
    "Purchase Cost": "9.50",
    "Qty": "100",
}


async def test_import_products_creates_valid_rows() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    summary = await ImportProductsUseCase(uow).execute(
        business_id=business_id, rows=[VALID_ROW], column_mapping=MAPPING
    )

    assert summary.total_rows == 1
    assert summary.created == 1
    assert summary.skipped_duplicates == 0
    assert summary.errors == []
    products, total = await uow.products.list_for_business(business_id)
    assert total == 1
    assert products[0].sku == "WID-001"


async def test_import_products_skips_duplicates_by_sku() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    duplicate_row = dict(VALID_ROW, **{"SKU": "wid-001", "Name": "Widget (dup)"})

    summary = await ImportProductsUseCase(uow).execute(
        business_id=business_id, rows=[VALID_ROW, duplicate_row], column_mapping=MAPPING
    )

    assert summary.created == 1
    assert summary.skipped_duplicates == 1


async def test_import_products_reports_missing_required_field() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    incomplete_row = dict(VALID_ROW)
    incomplete_row["SKU"] = ""

    summary = await ImportProductsUseCase(uow).execute(
        business_id=business_id, rows=[incomplete_row], column_mapping=MAPPING
    )

    assert summary.created == 0
    assert len(summary.errors) == 1
    assert summary.errors[0].row_number == 1
    assert "sku" in summary.errors[0].message


async def test_import_products_reports_invalid_numeric_value() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    bad_row = dict(VALID_ROW, **{"Selling Price": "not-a-number"})

    summary = await ImportProductsUseCase(uow).execute(
        business_id=business_id, rows=[bad_row], column_mapping=MAPPING
    )

    assert summary.created == 0
    assert len(summary.errors) == 1
    assert summary.errors[0].row_number == 1


async def test_import_products_remaps_columns() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    row = {
        "Product": "Widget",
        "Code": "WID-001",
        "Price": "19.99",
        "Cost": "9.50",
    }
    mapping = {
        "name": "Product",
        "sku": "Code",
        "selling_price": "Price",
        "purchase_cost": "Cost",
    }

    summary = await ImportProductsUseCase(uow).execute(
        business_id=business_id, rows=[row], column_mapping=mapping
    )

    assert summary.created == 1
    products, _ = await uow.products.list_for_business(business_id)
    assert products[0].name == "Widget"
    assert products[0].sku == "WID-001"
