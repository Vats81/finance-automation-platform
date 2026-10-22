"""Found by a live probe: a negative unit price, a negative tax, or a discount
larger than the subtotal were all accepted and produced negative sales - the
dashboard showed revenue of -$38.70. They are now rejected in the domain, so
every entry point (API, CSV import, edits) is covered.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.expenses.domain.entities import Expense
from app.expenses.domain.value_objects import PaymentMethod
from app.purchases.domain.entities import Purchase
from app.purchases.domain.value_objects import PurchaseLineItem
from app.sales.domain.entities import Sale
from app.sales.domain.value_objects import SaleLineItem
from app.shared.domain.exceptions import ValidationException
from app.shared.domain.value_objects import Money


def _money(value: str) -> Money:
    return Money(amount=Decimal(value))


def _sale(price: str = "100", qty: str = "1", discount: str | None = None, tax: str | None = None) -> Sale:
    return Sale.create(
        business_id=uuid.uuid4(),
        invoice_number="INV-1",
        customer_id=None,
        invoice_date=date(2026, 10, 1),
        due_date=None,
        line_items=[
            SaleLineItem(line_number=1, description="x", quantity=Decimal(qty), unit_price=_money(price))
        ],
        discount=_money(discount) if discount else None,
        tax=_money(tax) if tax else None,
    )


def test_a_normal_sale_with_discount_and_tax_is_fine() -> None:
    assert _sale("100", "2", discount="50", tax="10").total_amount == _money("160")


def test_decimal_arithmetic_is_exact() -> None:
    sale = Sale.create(
        business_id=uuid.uuid4(),
        invoice_number="INV-2",
        customer_id=None,
        invoice_date=date(2026, 10, 1),
        due_date=None,
        line_items=[
            SaleLineItem(line_number=1, description="a", quantity=Decimal("1"), unit_price=_money("0.10")),
            SaleLineItem(line_number=2, description="b", quantity=Decimal("1"), unit_price=_money("0.20")),
        ],
    )

    assert sale.total_amount == _money("0.30")  # 0.1 + 0.2 != 0.3 in binary floats


@pytest.mark.parametrize(
    "kwargs",
    [
        {"price": "-5"},
        {"qty": "0"},
        {"qty": "-1"},
        {"qty": "1000000001"},
        {"discount": "-1"},
        {"tax": "-5"},
        {"price": "10", "discount": "10.01"},
    ],
)
def test_invalid_sales_are_rejected(kwargs: dict[str, str]) -> None:
    with pytest.raises(ValidationException):
        _sale(**kwargs)


def test_a_discount_equal_to_the_subtotal_is_allowed() -> None:
    assert _sale("10", discount="10").total_amount == _money("0")


def test_editing_a_sale_cannot_introduce_a_negative_total() -> None:
    sale = _sale("100")
    item = SaleLineItem(line_number=1, description="x", quantity=Decimal("1"), unit_price=_money("10"))

    with pytest.raises(ValidationException):
        sale.update_details(
            invoice_number="INV-1",
            customer_id=None,
            invoice_date=date(2026, 10, 1),
            due_date=None,
            line_items=[item],
            discount=_money("50"),
            tax=_money("0"),
            notes=None,
        )


def test_purchases_reject_negative_costs_and_tax() -> None:
    with pytest.raises(ValidationException):
        PurchaseLineItem(line_number=1, description="x", quantity=Decimal("1"), unit_cost=_money("-1"))

    item = PurchaseLineItem(line_number=1, description="x", quantity=Decimal("1"), unit_cost=_money("5"))
    with pytest.raises(ValidationException):
        Purchase.create(
            business_id=uuid.uuid4(),
            purchase_number="P-1",
            vendor_id=uuid.uuid4(),
            purchase_date=date(2026, 10, 1),
            due_date=None,
            line_items=[item],
            tax=_money("-1"),
        )


def test_expenses_must_be_positive_with_non_negative_tax() -> None:
    def create(amount: str, tax: str | None = None) -> Expense:
        return Expense.create(
            business_id=uuid.uuid4(),
            expense_date=date(2026, 10, 1),
            category="Rent",
            description="x",
            amount=_money(amount),
            payment_method=PaymentMethod.CASH,
            tax=_money(tax) if tax else None,
        )

    assert create("10", "1").total_amount == _money("11")
    for amount, tax in (("0", None), ("-1", None), ("10", "-1")):
        with pytest.raises(ValidationException):
            create(amount, tax)

    expense = create("10")
    with pytest.raises(ValidationException):
        expense.update_details(amount=_money("0"))
    with pytest.raises(ValidationException):
        expense.update_details(tax=_money("-2"))


# ---- a purchase may name its supplier by typed text (scanned bills from one-off shops)


def _purchase(vendor_id: uuid.UUID | None, vendor_name: str | None) -> Purchase:
    item = PurchaseLineItem(line_number=1, description="Flour", quantity=Decimal("4"), unit_cost=_money("20"))
    return Purchase.create(
        business_id=uuid.uuid4(),
        purchase_number="P-1",
        vendor_id=vendor_id,
        purchase_date=date(2026, 10, 1),
        due_date=None,
        line_items=[item],
        vendor_name=vendor_name,
    )


def test_a_purchase_can_be_recorded_with_only_a_typed_vendor_name() -> None:
    purchase = _purchase(None, "  Corner   Wholesale  ")

    assert purchase.vendor_id is None
    assert purchase.vendor_name == "Corner Wholesale"  # whitespace tidied


def test_a_saved_vendor_wins_over_a_typed_name() -> None:
    vendor_id = uuid.uuid4()

    purchase = _purchase(vendor_id, "ignored text")

    assert purchase.vendor_id == vendor_id and purchase.vendor_name is None


@pytest.mark.parametrize("name", [None, "", "   ", "x" * 201])
def test_a_purchase_without_a_usable_vendor_is_rejected(name: str | None) -> None:
    with pytest.raises(ValidationException):
        _purchase(None, name)


def test_editing_a_purchase_can_switch_between_a_typed_and_a_saved_vendor() -> None:
    purchase = _purchase(None, "Corner Wholesale")
    vendor_id = uuid.uuid4()
    item = PurchaseLineItem(line_number=1, description="Flour", quantity=Decimal("4"), unit_cost=_money("20"))

    purchase.update_details(
        purchase_number="P-1",
        vendor_id=vendor_id,
        vendor_name=None,
        purchase_date=date(2026, 10, 1),
        due_date=None,
        line_items=[item],
        tax=_money("0"),
        notes=None,
    )
    assert purchase.vendor_id == vendor_id and purchase.vendor_name is None

    with pytest.raises(ValidationException):
        purchase.update_details(
            purchase_number="P-1",
            vendor_id=None,
            vendor_name="",
            purchase_date=date(2026, 10, 1),
            due_date=None,
            line_items=[item],
            tax=_money("0"),
            notes=None,
        )
