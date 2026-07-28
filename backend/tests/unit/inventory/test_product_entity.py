import uuid
from decimal import Decimal

import pytest

from app.inventory.domain.entities import Product
from app.inventory.domain.exceptions import NegativeStockException
from app.inventory.domain.value_objects import ProductStatus
from app.shared.domain.value_objects import Money


def make_product(**overrides) -> Product:
    defaults = dict(
        business_id=uuid.uuid4(),
        name="Widget",
        sku="WID-001",
        selling_price=Money(amount=Decimal("25")),
        purchase_cost=Money(amount=Decimal("10")),
        current_quantity=Decimal("10"),
        minimum_stock_level=Decimal("5"),
    )
    defaults.update(overrides)
    product = Product.create(**defaults)
    product.pull_domain_events()
    return product


def test_create_defaults_to_active_and_records_event() -> None:
    product = Product.create(
        business_id=uuid.uuid4(),
        name="Widget",
        sku="WID-001",
        selling_price=Money(amount=Decimal("25")),
        purchase_cost=Money(amount=Decimal("10")),
    )

    assert product.status == ProductStatus.ACTIVE
    assert product.is_active
    events = product.pull_domain_events()
    assert [e.event_type for e in events] == ["ProductCreated"]


def test_stock_thresholds() -> None:
    in_stock = make_product(current_quantity=Decimal("10"), minimum_stock_level=Decimal("5"))
    assert in_stock.is_low_stock is False
    assert in_stock.is_out_of_stock is False

    low = make_product(current_quantity=Decimal("3"), minimum_stock_level=Decimal("5"))
    assert low.is_low_stock is True
    assert low.is_out_of_stock is False

    out = make_product(current_quantity=Decimal("0"), minimum_stock_level=Decimal("5"))
    assert out.is_out_of_stock is True
    assert out.is_low_stock is False


def test_stock_value_is_purchase_cost_times_quantity() -> None:
    product = make_product(purchase_cost=Money(amount=Decimal("10")), current_quantity=Decimal("4"))
    assert product.stock_value == Money(amount=Decimal("40"))


def test_update_details_only_records_event_when_something_changed() -> None:
    product = make_product()

    product.update_details(name="Widget")  # unchanged
    assert product.pull_domain_events() == []

    product.update_details(name="Widget Pro", category="Hardware")
    events = product.pull_domain_events()
    assert len(events) == 1
    assert set(events[0].changed_fields) == {"name", "category"}


def test_adjust_stock_up_and_down() -> None:
    product = make_product(current_quantity=Decimal("10"))

    product.adjust_stock(delta=Decimal("5"), reason="received shipment")
    assert product.current_quantity == Decimal("15")
    events = product.pull_domain_events()
    assert [e.event_type for e in events] == ["StockAdjusted"]

    product.adjust_stock(delta=Decimal("-3"), reason="damaged")
    assert product.current_quantity == Decimal("12")


def test_adjust_stock_below_zero_raises() -> None:
    product = make_product(current_quantity=Decimal("2"))

    with pytest.raises(NegativeStockException):
        product.adjust_stock(delta=Decimal("-3"), reason="write-off")

    assert product.current_quantity == Decimal("2")  # unchanged on rejection


def test_deactivate_then_reactivate() -> None:
    product = make_product()

    product.deactivate()
    assert product.status == ProductStatus.INACTIVE
    events = product.pull_domain_events()
    assert [e.event_type for e in events] == ["ProductDeactivated"]

    product.reactivate()
    assert product.is_active is True
