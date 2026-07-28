from decimal import Decimal

import pytest

from app.shared.domain.exceptions import ValidationException
from app.shared.domain.value_objects import Money


def test_money_rounds_to_cents() -> None:
    money = Money(amount=Decimal("10.005"))

    assert money.amount == Decimal("10.01")


def test_money_from_cents_round_trips() -> None:
    money = Money.from_cents(1050)

    assert money.amount == Decimal("10.50")
    assert money.cents == 1050


def test_money_addition_and_subtraction() -> None:
    a = Money(amount=Decimal("10.00"))
    b = Money(amount=Decimal("2.50"))

    assert (a + b).amount == Decimal("12.50")
    assert (a - b).amount == Decimal("7.50")


def test_money_multiplication_by_quantity() -> None:
    unit_price = Money(amount=Decimal("3.00"))

    assert (unit_price * 4).amount == Decimal("12.00")


def test_money_comparison() -> None:
    a = Money(amount=Decimal("5.00"))
    b = Money(amount=Decimal("10.00"))

    assert a < b
    assert b > a
    assert a <= Money(amount=Decimal("5.00"))


def test_money_rejects_non_usd_currency() -> None:
    with pytest.raises(ValidationException):
        Money(amount=Decimal("10.00"), currency="EUR")
