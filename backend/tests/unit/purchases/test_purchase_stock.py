"""Adding a purchase's counts to stock, and keeping stock honest afterwards."""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.inventory.application.commands.create_product import CreateProductCommand, CreateProductUseCase
from app.inventory.domain.exceptions import ProductNotFoundException
from app.purchases.application.commands.create_purchase import (
    CreatePurchaseCommand,
    CreatePurchaseLineItemInput,
    CreatePurchaseUseCase,
)
from app.purchases.application.commands.update_purchase import (
    UpdatePurchaseCommand,
    UpdatePurchaseLineItemInput,
    UpdatePurchaseUseCase,
)
from app.purchases.application.commands.void_purchase import VoidPurchaseCommand, VoidPurchaseUseCase
from app.purchases.domain.exceptions import PurchaseStockLockedException, StockAlreadyUsedException
from app.shared.domain.exceptions import ValidationException
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


async def _business(uow: FakeUnitOfWork) -> uuid.UUID:
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Bakery")
    )
    return business.id


async def _product(uow: FakeUnitOfWork, business_id: uuid.UUID, sku: str, quantity: str = "10"):
    return await CreateProductUseCase(uow).execute(
        CreateProductCommand(
            business_id=business_id,
            name=f"Product {sku}",
            sku=sku,
            selling_price=Decimal("5"),
            purchase_cost=Decimal("2"),
            current_quantity=Decimal(quantity),
        )
    )


def _create(
    business_id: uuid.UUID, lines: list[tuple[str, str, uuid.UUID | None]], **kw
) -> CreatePurchaseCommand:
    return CreatePurchaseCommand(
        business_id=business_id,
        purchase_number=kw.pop("number", "P-1"),
        vendor_id=None,
        vendor_name="Corner Wholesale",
        purchase_date=date(2026, 10, 20),
        line_items=[
            CreatePurchaseLineItemInput(i + 1, desc, Decimal(qty), Decimal("2.00"), pid)
            for i, (desc, qty, pid) in enumerate(lines)
        ],
        **kw,
    )


async def _stock(uow: FakeUnitOfWork, business_id: uuid.UUID, product_id: uuid.UUID) -> Decimal:
    product = await uow.products.get_by_id_for_business(product_id, business_id)
    assert product is not None
    return product.current_quantity


async def test_confirming_with_add_to_stock_increases_each_linked_products_stock() -> None:
    uow = FakeUnitOfWork()
    biz = await _business(uow)
    flour, sugar = await _product(uow, biz, "F"), await _product(uow, biz, "S", "0")

    purchase = await CreatePurchaseUseCase(uow).execute(
        _create(
            biz,
            [("Flour", "6", flour.id), ("Sugar", "3.5", sugar.id), ("Eggs", "2", None)],
            add_to_stock=True,
        )
    )

    assert purchase.stock_added is True
    assert await _stock(uow, biz, flour.id) == Decimal("16")
    assert await _stock(uow, biz, sugar.id) == Decimal("3.5")


async def test_without_the_option_the_link_is_recorded_but_stock_is_untouched() -> None:
    uow = FakeUnitOfWork()
    biz = await _business(uow)
    flour = await _product(uow, biz, "F")

    purchase = await CreatePurchaseUseCase(uow).execute(_create(biz, [("Flour", "6", flour.id)]))

    assert purchase.stock_added is False
    assert await _stock(uow, biz, flour.id) == Decimal("10")


async def test_add_to_stock_with_no_linked_lines_changes_nothing() -> None:
    uow = FakeUnitOfWork()
    biz = await _business(uow)

    purchase = await CreatePurchaseUseCase(uow).execute(
        _create(biz, [("Eggs", "2", None)], add_to_stock=True)
    )

    assert purchase.stock_added is False


async def test_a_product_from_another_business_is_refused_even_as_a_plain_link() -> None:
    uow = FakeUnitOfWork()
    mine, theirs = await _business(uow), await _business(uow)
    their_product = await _product(uow, theirs, "X")

    with pytest.raises(ProductNotFoundException):
        await CreatePurchaseUseCase(uow).execute(_create(mine, [("Flour", "1", their_product.id)]))
    with pytest.raises(ProductNotFoundException):
        await CreatePurchaseUseCase(uow).execute(
            _create(mine, [("Flour", "1", their_product.id)], add_to_stock=True)
        )

    assert await _stock(uow, theirs, their_product.id) == Decimal("10")


async def test_more_than_four_decimal_places_cannot_be_added_to_stock() -> None:
    uow = FakeUnitOfWork()
    biz = await _business(uow)
    flour = await _product(uow, biz, "F")

    with pytest.raises(ValidationException):
        await CreatePurchaseUseCase(uow).execute(
            _create(biz, [("Flour", "1.00001", flour.id)], add_to_stock=True)
        )

    assert await _stock(uow, biz, flour.id) == Decimal("10")


async def test_voiding_takes_the_added_stock_back_out() -> None:
    uow = FakeUnitOfWork()
    biz = await _business(uow)
    flour = await _product(uow, biz, "F")
    purchase = await CreatePurchaseUseCase(uow).execute(
        _create(biz, [("Flour", "6", flour.id)], add_to_stock=True)
    )

    await VoidPurchaseUseCase(uow).execute(VoidPurchaseCommand(business_id=biz, purchase_id=purchase.id))

    assert await _stock(uow, biz, flour.id) == Decimal("10")


async def test_voiding_is_refused_when_the_stock_has_already_been_used() -> None:
    uow = FakeUnitOfWork()
    biz = await _business(uow)
    flour = await _product(uow, biz, "F", "0")
    purchase = await CreatePurchaseUseCase(uow).execute(
        _create(biz, [("Flour", "6", flour.id)], add_to_stock=True)
    )
    product = await uow.products.get_by_id_for_business(flour.id, biz)
    assert product is not None
    product.adjust_stock(delta=Decimal("-4"), reason="sold")  # only 2 of the 6 remain
    await uow.products.update(product)

    with pytest.raises(StockAlreadyUsedException, match="only 2"):
        await VoidPurchaseUseCase(uow).execute(VoidPurchaseCommand(business_id=biz, purchase_id=purchase.id))

    assert await _stock(uow, biz, flour.id) == Decimal("2")  # untouched
    refreshed = await uow.purchases.get_by_id_for_business(purchase.id, biz)
    assert refreshed is not None and refreshed.status.value == "recorded"


async def test_voiding_a_purchase_that_added_no_stock_leaves_stock_alone() -> None:
    uow = FakeUnitOfWork()
    biz = await _business(uow)
    flour = await _product(uow, biz, "F")
    purchase = await CreatePurchaseUseCase(uow).execute(_create(biz, [("Flour", "6", flour.id)]))

    await VoidPurchaseUseCase(uow).execute(VoidPurchaseCommand(business_id=biz, purchase_id=purchase.id))

    assert await _stock(uow, biz, flour.id) == Decimal("10")


def _update(
    business_id: uuid.UUID, purchase_id: uuid.UUID, qty: str, pid: uuid.UUID, vendor: str
) -> UpdatePurchaseCommand:
    return UpdatePurchaseCommand(
        business_id=business_id,
        purchase_id=purchase_id,
        purchase_number="P-1",
        vendor_id=None,
        vendor_name=vendor,
        purchase_date=date(2026, 10, 20),
        line_items=[UpdatePurchaseLineItemInput(1, "Flour", Decimal(qty), Decimal("2.00"), pid)],
    )


async def test_a_purchase_that_added_stock_keeps_its_items_but_other_details_can_change() -> None:
    uow = FakeUnitOfWork()
    biz = await _business(uow)
    flour = await _product(uow, biz, "F")
    purchase = await CreatePurchaseUseCase(uow).execute(
        _create(biz, [("Flour", "6", flour.id)], add_to_stock=True)
    )

    renamed = await UpdatePurchaseUseCase(uow).execute(
        _update(biz, purchase.id, "6", flour.id, "New Vendor Ltd")
    )
    assert renamed.vendor_name == "New Vendor Ltd"

    with pytest.raises(PurchaseStockLockedException):
        await UpdatePurchaseUseCase(uow).execute(_update(biz, purchase.id, "9", flour.id, "New Vendor Ltd"))
    assert await _stock(uow, biz, flour.id) == Decimal("16")


async def test_editing_cannot_link_another_businesses_product() -> None:
    uow = FakeUnitOfWork()
    mine, theirs = await _business(uow), await _business(uow)
    purchase = await CreatePurchaseUseCase(uow).execute(_create(mine, [("Flour", "1", None)]))
    their_product = await _product(uow, theirs, "X")

    with pytest.raises(ProductNotFoundException):
        await UpdatePurchaseUseCase(uow).execute(_update(mine, purchase.id, "1", their_product.id, "V"))


async def test_voiding_twice_does_not_take_the_stock_out_twice() -> None:
    from app.purchases.domain.exceptions import PurchaseAlreadyVoidException

    uow = FakeUnitOfWork()
    biz = await _business(uow)
    flour = await _product(uow, biz, "F")
    purchase = await CreatePurchaseUseCase(uow).execute(
        _create(biz, [("Flour", "6", flour.id)], add_to_stock=True)
    )
    void = VoidPurchaseCommand(business_id=biz, purchase_id=purchase.id)
    await VoidPurchaseUseCase(uow).execute(void)

    with pytest.raises(PurchaseAlreadyVoidException):
        await VoidPurchaseUseCase(uow).execute(void)

    assert await _stock(uow, biz, flour.id) == Decimal("10")
