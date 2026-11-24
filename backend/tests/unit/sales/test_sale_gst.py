"""GST on a sale: a rate per line, tax worked out per rate, and the state it is supplied to."""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.sales.api.schemas import SaleResponse
from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
from app.sales.application.commands.update_sale import (
    UpdateSaleCommand,
    UpdateSaleLineItemInput,
    UpdateSaleUseCase,
)
from app.shared.domain.exceptions import ValidationException
from app.shared.domain.gst import split_tax
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

BUSINESS = uuid.uuid4()


def _line(
    n: int, price: str, rate: str | None, qty: str = "1", hsn: str | None = None
) -> CreateSaleLineItemInput:
    return CreateSaleLineItemInput(
        line_number=n,
        description=f"Item {n}",
        quantity=Decimal(qty),
        unit_price=Decimal(price),
        gst_rate=Decimal(rate) if rate is not None else None,
        hsn_code=hsn,
    )


def _sale(lines: list[CreateSaleLineItemInput], **extra: object) -> CreateSaleCommand:
    fields: dict = dict(
        business_id=BUSINESS, invoice_number="INV-1", invoice_date=date(2026, 11, 1), line_items=lines
    )
    fields.update(extra)
    return CreateSaleCommand(**fields)


async def test_tax_is_worked_out_from_the_rate_on_each_line() -> None:
    uow = FakeUnitOfWork()

    sale = await CreateSaleUseCase(uow).execute(_sale([_line(1, "1000", "18"), _line(2, "500", "5")]))

    assert sale.subtotal.amount == Decimal("1500.00")
    assert sale.tax.amount == Decimal("205.00")  # 180 + 25
    assert sale.total_amount.amount == Decimal("1705.00")
    groups = {g.rate: (g.taxable_value.amount, g.tax.amount) for g in sale.gst_groups}
    assert groups == {
        Decimal("5"): (Decimal("500.00"), Decimal("25.00")),
        Decimal("18"): (Decimal("1000.00"), Decimal("180.00")),
    }


async def test_a_discount_is_shared_over_the_lines_before_tax() -> None:
    uow = FakeUnitOfWork()

    sale = await CreateSaleUseCase(uow).execute(
        _sale([_line(1, "1000", "18"), _line(2, "500", "5")], discount=Decimal("150"))
    )

    # 100 off the first line and 50 off the second: taxed on 900 and 450
    assert sale.tax.amount == Decimal("184.50")  # 162 + 22.50
    assert sale.total_amount.amount == Decimal("1534.50")  # 1500 - 150 + 184.50


async def test_lines_at_the_same_rate_are_taxed_together() -> None:
    uow = FakeUnitOfWork()

    sale = await CreateSaleUseCase(uow).execute(
        _sale([_line(1, "33.33", "5"), _line(2, "33.33", "5"), _line(3, "33.34", "5")])
    )

    (group,) = sale.gst_groups
    assert group.taxable_value.amount == Decimal("100.00") and group.tax.amount == Decimal("5.00")


async def test_a_zero_rate_and_a_line_without_a_rate_carry_no_tax() -> None:
    uow = FakeUnitOfWork()

    sale = await CreateSaleUseCase(uow).execute(_sale([_line(1, "100", "0"), _line(2, "100", None)]))

    assert sale.tax.amount == Decimal("0.00") and sale.total_amount.amount == Decimal("200.00")


async def test_a_manual_tax_amount_cannot_be_added_to_gst_lines() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(ValidationException):
        await CreateSaleUseCase(uow).execute(_sale([_line(1, "100", "18")], tax=Decimal("5")))
    sale = await CreateSaleUseCase(uow).execute(_sale([_line(1, "100", "18")], tax=Decimal("0")))

    assert sale.tax.amount == Decimal("18.00")


async def test_a_sale_without_gst_rates_works_exactly_as_before() -> None:
    uow = FakeUnitOfWork()

    sale = await CreateSaleUseCase(uow).execute(_sale([_line(1, "100", None)], tax=Decimal("7.50")))

    assert sale.tax.amount == Decimal("7.50") and sale.total_amount.amount == Decimal("107.50")
    assert sale.gst_groups == []


@pytest.mark.parametrize("rate", ["7", "-1", "100", "18.5"])
async def test_only_real_gst_rates_are_accepted(rate: str) -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(ValidationException):
        await CreateSaleUseCase(uow).execute(_sale([_line(1, "100", rate)]))


@pytest.mark.parametrize("hsn", ["12", "123", "123456789", "12ab", " "])
async def test_an_hsn_code_has_four_to_eight_digits(hsn: str) -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(ValidationException):
        await CreateSaleUseCase(uow).execute(_sale([_line(1, "100", "18", hsn=hsn)]))
    sale = await CreateSaleUseCase(uow).execute(_sale([_line(1, "100", "18", hsn="999293")]))
    assert sale.line_items[0].hsn_code == "999293"


async def test_the_place_of_supply_must_be_a_real_state() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(ValidationException):
        await CreateSaleUseCase(uow).execute(_sale([_line(1, "100", "18")], place_of_supply="55"))
    sale = await CreateSaleUseCase(uow).execute(_sale([_line(1, "100", "18")], place_of_supply="29"))

    assert sale.place_of_supply == "29"


async def test_editing_a_sale_recalculates_its_tax() -> None:
    uow = FakeUnitOfWork()
    sale = await CreateSaleUseCase(uow).execute(_sale([_line(1, "100", "18")]))

    updated = await UpdateSaleUseCase(uow).execute(
        UpdateSaleCommand(
            business_id=BUSINESS,
            sale_id=sale.id,
            invoice_number="INV-1",
            invoice_date=date(2026, 11, 1),
            line_items=[
                UpdateSaleLineItemInput(
                    line_number=1,
                    description="Item 1",
                    quantity=Decimal("2"),
                    unit_price=Decimal("100"),
                    gst_rate=Decimal("12"),
                )
            ],
            place_of_supply="27",
        )
    )

    assert updated.tax.amount == Decimal("24.00") and updated.total_amount.amount == Decimal("224.00")
    assert updated.place_of_supply == "27"


async def test_the_response_carries_the_rates_and_the_breakdown() -> None:
    uow = FakeUnitOfWork()
    sale = await CreateSaleUseCase(uow).execute(
        _sale([_line(1, "1000", "18", hsn="999293")], place_of_supply="27")
    )

    response = SaleResponse.from_domain(sale)

    assert response.line_items[0].gst_rate == Decimal("18") and response.line_items[0].hsn_code == "999293"
    assert [(g.rate, g.taxable_value, g.tax) for g in response.gst_breakdown] == [
        (Decimal("18"), Decimal("1000.00"), Decimal("180.00"))
    ]
    assert response.place_of_supply == "27" and response.tax == Decimal("180.00")


@pytest.mark.parametrize(
    ("tax", "inter_state", "expected"),
    [
        ("184.50", False, ("92.25", "92.25", "0.00")),
        ("0.01", False, ("0.00", "0.01", "0.00")),
        ("0.03", False, ("0.01", "0.02", "0.00")),
        ("180.00", True, ("0.00", "0.00", "180.00")),
    ],
)
def test_tax_splits_into_cgst_and_sgst_or_is_all_igst(
    tax: str, inter_state: bool, expected: tuple[str, str, str]
) -> None:
    cgst, sgst, igst = split_tax(Decimal(tax), inter_state=inter_state)

    assert (str(cgst), str(sgst), str(igst)) == expected
    assert cgst + sgst + igst == Decimal(tax)  # never loses or invents a paisa
