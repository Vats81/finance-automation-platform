"""The printable invoice: what a customer sees when a GST invoice is downloaded or shared."""

import io
import uuid
from datetime import date
from decimal import Decimal

import pytest
from pypdf import PdfReader

from app.business.domain.entities import Business
from app.customers.domain.entities import Customer
from app.customers.domain.value_objects import CustomerAddress
from app.sales.application.invoice_pdf import generate_invoice_pdf
from app.sales.domain.entities import Sale
from app.sales.domain.value_objects import SaleLineItem
from app.shared.domain.money_words import number_to_words_indian, rupees_in_words
from app.shared.domain.value_objects import Money

SELLER_GSTIN = "27AAPFU0939F1ZV"  # Maharashtra


def _business(**details: object) -> Business:
    business = Business.register(owner_user_id=uuid.uuid4(), name="Sharma Traders", currency="INR")
    fields: dict = dict(
        gstin=SELLER_GSTIN,
        address_line="12 Market Road",
        city="Pune",
        pincode="411001",
        phone="9876543210",
        upi_id="sharma@upi",
    )
    fields.update(details)
    business.complete_onboarding(**fields)
    return business


def _line(n: int, price: str, rate: str | None, qty: str = "1", hsn: str | None = None) -> SaleLineItem:
    return SaleLineItem(
        line_number=n,
        description=f"Item {n}",
        quantity=Decimal(qty),
        unit_price=Money(amount=Decimal(price)),
        gst_rate=Decimal(rate) if rate is not None else None,
        hsn_code=hsn,
    )


def _sale(business: Business, lines: list[SaleLineItem], **extra: object) -> Sale:
    return Sale.create(
        business_id=business.id,
        invoice_number="INV-7",
        customer_id=None,
        invoice_date=date(2026, 11, 1),
        due_date=None,
        line_items=lines,
        **extra,
    )  # type: ignore[arg-type]


def _text(pdf: bytes) -> str:
    return " ".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf)).pages)


def _customer() -> Customer:
    return Customer.create(
        business_id=uuid.uuid4(),
        name="Asha Stores",
        phone="9123456780",
        address=CustomerAddress(
            street="5 Lake View", city="Bengaluru", state="Karnataka", postal_code="560001"
        ),
        gst_number="29AAACH7409R1ZX",
    )


def test_a_gst_invoice_shows_both_gstins_the_rates_and_the_split_within_a_state() -> None:
    business = _business()
    sale = _sale(business, [_line(1, "1000", "18", hsn="999293"), _line(2, "500", "5")], place_of_supply="27")

    text = _text(generate_invoice_pdf(business=business, sale=sale, customer=_customer()))

    assert "TAX INVOICE" in text and "INV-7" in text
    assert SELLER_GSTIN in text and "29AAACH7409R1ZX" in text
    assert "999293" in text and "Asha Stores" in text
    assert "CGST" in text and "SGST" in text and "IGST" not in text
    assert "Rs. 1,705.00" in text  # 1,500 + 205 tax
    assert "One Thousand Seven Hundred Five" in text


def test_an_invoice_to_another_state_shows_igst_only() -> None:
    business = _business()
    sale = _sale(business, [_line(1, "1000", "18")], place_of_supply="29")

    text = _text(generate_invoice_pdf(business=business, sale=sale, customer=_customer()))

    assert "IGST" in text and "CGST" not in text and "SGST" not in text


def test_an_invoice_without_gst_is_a_plain_invoice() -> None:
    business = _business(gstin="", gst_registered=False)
    sale = _sale(business, [_line(1, "250", None)])

    text = _text(generate_invoice_pdf(business=business, sale=sale, customer=None))

    assert "TAX INVOICE" not in text and "INVOICE" in text
    assert "GST" not in text and "Walk-in customer" in text


def test_a_payment_already_received_shows_the_balance_due() -> None:
    business = _business()
    sale = _sale(business, [_line(1, "1000", None)])
    sale.record_payment(Money(amount=Decimal("400")))

    text = _text(generate_invoice_pdf(business=business, sale=sale, customer=None))

    assert "Balance due" in text and "Rs. 600.00" in text


def test_a_void_invoice_is_marked_void() -> None:
    business = _business()
    sale = _sale(business, [_line(1, "100", None)])
    sale.void()

    assert "VOID" in _text(generate_invoice_pdf(business=business, sale=sale, customer=None))


def test_the_upi_qr_is_drawn_only_when_there_is_a_upi_id() -> None:
    with_upi = _business()
    without = _business(upi_id="")
    sale_a = _sale(with_upi, [_line(1, "100", None)])
    sale_b = _sale(without, [_line(1, "100", None)])

    assert "Pay by UPI" in _text(generate_invoice_pdf(business=with_upi, sale=sale_a, customer=None))
    assert "Pay by UPI" not in _text(generate_invoice_pdf(business=without, sale=sale_b, customer=None))


@pytest.mark.parametrize(
    ("number", "words"),
    [
        (0, "Zero"),
        (7, "Seven"),
        (19, "Nineteen"),
        (40, "Forty"),
        (101, "One Hundred One"),
        (1000, "One Thousand"),
        (123456, "One Lakh Twenty Three Thousand Four Hundred Fifty Six"),
        (10_000_000, "One Crore"),
        (1_00_00_00_000, "One Hundred Crore"),
    ],
)
def test_whole_numbers_are_written_the_indian_way(number: int, words: str) -> None:
    assert number_to_words_indian(number) == words


def test_an_amount_in_words_includes_the_paise() -> None:
    assert rupees_in_words(Decimal("1705.00")) == "Rupees One Thousand Seven Hundred Five Only"
    assert rupees_in_words(Decimal("12.50")) == "Rupees Twelve and Fifty Paise Only"
