import uuid
from decimal import Decimal

import pytest

from app.inventory.application.commands.adjust_stock import AdjustStockCommand, AdjustStockUseCase
from app.inventory.application.commands.create_product import CreateProductCommand, CreateProductUseCase
from app.inventory.application.commands.deactivate_product import (
    DeactivateProductCommand,
    DeactivateProductUseCase,
)
from app.inventory.application.commands.reactivate_product import (
    ReactivateProductCommand,
    ReactivateProductUseCase,
)
from app.inventory.application.commands.update_product import UpdateProductCommand, UpdateProductUseCase
from app.inventory.application.queries.get_product import GetProductQuery, GetProductUseCase
from app.inventory.application.queries.list_products import ListProductsQuery, ListProductsUseCase
from app.inventory.domain.exceptions import NegativeStockException, ProductNotFoundException
from app.inventory.domain.value_objects import ProductStatus
from app.shared.application.pagination import PageRequest
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


def make_create_command(business_id: uuid.UUID, **overrides) -> CreateProductCommand:
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


async def test_create_and_get_product() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    created = await CreateProductUseCase(uow).execute(make_create_command(business_id))

    fetched = await GetProductUseCase(uow).execute(
        GetProductQuery(business_id=business_id, product_id=created.id)
    )
    assert fetched.name == "Widget"
    assert fetched.is_low_stock is False


async def test_get_product_from_wrong_business_raises() -> None:
    uow = FakeUnitOfWork()
    product = await CreateProductUseCase(uow).execute(make_create_command(uuid.uuid4()))

    with pytest.raises(ProductNotFoundException):
        await GetProductUseCase(uow).execute(
            GetProductQuery(business_id=uuid.uuid4(), product_id=product.id)
        )


async def test_list_products_is_scoped_per_business() -> None:
    uow = FakeUnitOfWork()
    business_a = uuid.uuid4()
    business_b = uuid.uuid4()
    await CreateProductUseCase(uow).execute(make_create_command(business_a, sku="A-1"))
    await CreateProductUseCase(uow).execute(make_create_command(business_b, sku="B-1"))

    page = await ListProductsUseCase(uow).execute(
        ListProductsQuery(business_id=business_a, page=PageRequest())
    )

    assert page.total == 1
    assert page.items[0].sku == "A-1"


async def test_update_product() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    product = await CreateProductUseCase(uow).execute(make_create_command(business_id))

    updated = await UpdateProductUseCase(uow).execute(
        UpdateProductCommand(business_id=business_id, product_id=product.id, name="Widget Pro")
    )

    assert updated.name == "Widget Pro"


async def test_adjust_stock_use_case() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    product = await CreateProductUseCase(uow).execute(make_create_command(business_id))

    adjusted = await AdjustStockUseCase(uow).execute(
        AdjustStockCommand(
            business_id=business_id, product_id=product.id, delta=Decimal("5"), reason="restock"
        )
    )

    assert adjusted.current_quantity == Decimal("15")


async def test_adjust_stock_use_case_rejects_negative_result() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    product = await CreateProductUseCase(uow).execute(
        make_create_command(business_id, current_quantity=Decimal("2"))
    )

    with pytest.raises(NegativeStockException):
        await AdjustStockUseCase(uow).execute(
            AdjustStockCommand(
                business_id=business_id, product_id=product.id, delta=Decimal("-5"), reason="write-off"
            )
        )


async def test_deactivate_and_reactivate_product() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    product = await CreateProductUseCase(uow).execute(make_create_command(business_id))

    deactivated = await DeactivateProductUseCase(uow).execute(
        DeactivateProductCommand(business_id=business_id, product_id=product.id)
    )
    assert deactivated.status == ProductStatus.INACTIVE

    reactivated = await ReactivateProductUseCase(uow).execute(
        ReactivateProductCommand(business_id=business_id, product_id=product.id)
    )
    assert reactivated.status == ProductStatus.ACTIVE
