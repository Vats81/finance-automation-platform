import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from app.inventory.application.commands.create_product import CreateProductCommand, CreateProductUseCase
from app.notifications.application.queries.list_notifications import (
    GetNotificationsQuery,
    ListNotificationsUseCase,
)
from app.purchases.application.commands.create_purchase import (
    CreatePurchaseCommand,
    CreatePurchaseLineItemInput,
    CreatePurchaseUseCase,
)
from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
from app.sales.application.commands.void_sale import VoidSaleCommand, VoidSaleUseCase
from tests.fakes.fake_ports import FakeClock
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

_NOW = datetime(2026, 7, 27, tzinfo=timezone.utc)


def make_sale_command(business_id: uuid.UUID, **overrides) -> CreateSaleCommand:
    defaults = dict(
        business_id=business_id,
        invoice_number="INV-001",
        invoice_date=date(2026, 6, 1),
        line_items=[
            CreateSaleLineItemInput(
                line_number=1, description="Widget", quantity=Decimal("1"), unit_price=Decimal("500")
            )
        ],
    )
    defaults.update(overrides)
    return CreateSaleCommand(**defaults)


def make_purchase_command(business_id: uuid.UUID, **overrides) -> CreatePurchaseCommand:
    defaults = dict(
        business_id=business_id,
        purchase_number="PO-001",
        vendor_id=uuid.uuid4(),
        purchase_date=date(2026, 6, 1),
        line_items=[
            CreatePurchaseLineItemInput(
                line_number=1, description="Raw materials", quantity=Decimal("1"), unit_cost=Decimal("300")
            )
        ],
    )
    defaults.update(overrides)
    return CreatePurchaseCommand(**defaults)


def make_product_command(business_id: uuid.UUID, **overrides) -> CreateProductCommand:
    defaults = dict(
        business_id=business_id,
        name="Widget",
        sku="WID-001",
        selling_price=Decimal("25"),
        purchase_cost=Decimal("10"),
        current_quantity=Decimal("10"),
        minimum_stock_level=Decimal("5"),
    )
    defaults.update(overrides)
    return CreateProductCommand(**defaults)


async def test_sale_overdue_by_more_than_a_week_is_critical() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    sale = await CreateSaleUseCase(uow).execute(
        make_sale_command(business_id, due_date=date(2026, 7, 10))  # 17 days overdue at _NOW
    )

    notifications = await ListNotificationsUseCase(uow, FakeClock(_NOW)).execute(
        GetNotificationsQuery(business_id=business_id)
    )

    assert notifications.count == 1
    item = notifications.items[0]
    assert item.category == "overdue_sale"
    assert item.severity == "critical"
    assert item.id == f"overdue_sale:{sale.id}"
    assert "INV-001" in item.message
    assert "17 day" in item.message
    assert "500" in item.message
    assert item.link == f"/app/sales/{sale.id}"


async def test_sale_overdue_by_a_few_days_is_warning() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    await CreateSaleUseCase(uow).execute(
        make_sale_command(business_id, due_date=date(2026, 7, 24))  # 3 days overdue
    )

    notifications = await ListNotificationsUseCase(uow, FakeClock(_NOW)).execute(
        GetNotificationsQuery(business_id=business_id)
    )

    assert notifications.items[0].severity == "warning"


async def test_purchase_overdue_is_critical_and_symmetric() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    purchase = await CreatePurchaseUseCase(uow).execute(
        make_purchase_command(business_id, due_date=date(2026, 7, 1))  # 26 days overdue
    )

    notifications = await ListNotificationsUseCase(uow, FakeClock(_NOW)).execute(
        GetNotificationsQuery(business_id=business_id)
    )

    assert notifications.count == 1
    item = notifications.items[0]
    assert item.category == "overdue_purchase"
    assert item.severity == "critical"
    assert "PO-001" in item.message
    assert item.link == f"/app/purchases/{purchase.id}"


async def test_out_of_stock_is_critical_and_low_stock_is_warning() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    out_of_stock = await CreateProductUseCase(uow).execute(
        make_product_command(business_id, name="Out Widget", sku="OUT-1", current_quantity=Decimal("0"))
    )
    await CreateProductUseCase(uow).execute(
        make_product_command(
            business_id,
            name="Low Widget",
            sku="LOW-1",
            current_quantity=Decimal("2"),
            minimum_stock_level=Decimal("5"),
        )
    )

    notifications = await ListNotificationsUseCase(uow, FakeClock(_NOW)).execute(
        GetNotificationsQuery(business_id=business_id)
    )

    by_category = {n.id: n for n in notifications.items}
    out_item = by_category[f"low_stock:{out_of_stock.id}"]
    assert out_item.severity == "critical"
    assert "out of stock" in out_item.message
    low_item = next(n for n in notifications.items if "Low Widget" in n.message)
    assert low_item.severity == "warning"
    assert "2 left" in low_item.message


async def test_excludes_no_due_date_future_due_date_and_paid_sales() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    await CreateSaleUseCase(uow).execute(
        make_sale_command(business_id, invoice_number="NO-DUE-DATE", due_date=None)
    )
    await CreateSaleUseCase(uow).execute(
        make_sale_command(business_id, invoice_number="NOT-YET-DUE", due_date=date(2026, 12, 1))
    )
    voided = await CreateSaleUseCase(uow).execute(
        make_sale_command(business_id, invoice_number="VOIDED", due_date=date(2026, 1, 1))
    )
    await VoidSaleUseCase(uow).execute(VoidSaleCommand(business_id=business_id, sale_id=voided.id))

    notifications = await ListNotificationsUseCase(uow, FakeClock(_NOW)).execute(
        GetNotificationsQuery(business_id=business_id)
    )

    assert notifications.count == 0


async def test_empty_business_has_no_notifications() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    notifications = await ListNotificationsUseCase(uow, FakeClock(_NOW)).execute(
        GetNotificationsQuery(business_id=business_id)
    )

    assert notifications.count == 0
    assert notifications.items == []


async def test_critical_items_sort_before_warning_items() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    await CreateSaleUseCase(uow).execute(
        make_sale_command(business_id, invoice_number="WARNING", due_date=date(2026, 7, 25))
    )
    await CreatePurchaseUseCase(uow).execute(
        make_purchase_command(business_id, purchase_number="CRITICAL", due_date=date(2026, 6, 1))
    )

    notifications = await ListNotificationsUseCase(uow, FakeClock(_NOW)).execute(
        GetNotificationsQuery(business_id=business_id)
    )

    assert [n.severity for n in notifications.items] == ["critical", "warning"]
