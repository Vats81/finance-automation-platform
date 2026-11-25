"""A small business's supplier needs only a name; whatever else is given is still checked."""

import uuid

import pytest

from app.shared.domain.exceptions import ValidationException
from app.vendors.api.schemas import CreateBusinessVendorRequest, VendorResponse
from app.vendors.application.commands.create_business_vendor import (
    CreateBusinessVendorCommand,
    CreateBusinessVendorUseCase,
)
from app.vendors.domain.value_objects import TaxId
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

BUSINESS = uuid.uuid4()
GSTIN = "27AAPFU0939F1ZV"


async def _create(**fields: object):
    command = CreateBusinessVendorCommand(business_id=BUSINESS, **fields)  # type: ignore[arg-type]
    return await CreateBusinessVendorUseCase(FakeUnitOfWork()).execute(command)


async def test_a_name_is_enough() -> None:
    vendor = await _create(legal_name="  Gupta   Wholesale ")

    response = VendorResponse.from_domain(vendor)
    assert response.legal_name == "Gupta Wholesale"
    assert response.contact_email == "" and response.tax_id_masked == "" and response.address.street == ""


async def test_a_blank_name_is_refused() -> None:
    with pytest.raises(ValidationException):
        await _create(legal_name="   ")


@pytest.mark.parametrize(
    ("typed", "stored", "shown"),
    [
        (GSTIN.lower(), GSTIN, GSTIN),  # printed on every invoice, so shown as it is
        (" aapfu 0939f ", "AAPFU0939F", "******939F"),
        ("12-3456789", "12-3456789", "**-***6789"),
    ],
)
async def test_an_indian_or_us_tax_number_is_accepted(typed: str, stored: str, shown: str) -> None:
    vendor = await _create(legal_name="A", tax_id=typed)

    assert vendor.tax_id.unmasked == stored
    assert vendor.tax_id.masked() == shown


@pytest.mark.parametrize("bad", ["27AAPFU0939F1ZW", "hello", "123", "AAPFU0939", GSTIN + "9"])
async def test_a_mistyped_tax_number_is_refused(bad: str) -> None:
    with pytest.raises(ValidationException):
        await _create(legal_name="A", tax_id=bad)


def test_a_tax_number_is_never_accepted_empty() -> None:
    with pytest.raises(ValidationException):
        TaxId("")


async def test_a_bad_email_is_refused() -> None:
    with pytest.raises(ValidationException):
        await _create(legal_name="A", contact_email="not-an-email")


async def test_an_address_is_all_or_nothing() -> None:
    with pytest.raises(ValidationException):
        await _create(legal_name="A", city="Pune")

    vendor = await _create(
        legal_name="A", street="1 Road", city="Pune", state="Maharashtra", postal_code="411001", country="IN"
    )
    assert vendor.address.city == "Pune" and vendor.address.country == "IN"


def test_blank_email_and_tax_id_from_a_form_count_as_not_given() -> None:
    body = CreateBusinessVendorRequest(legal_name="A", contact_email="", tax_id="  ")

    assert body.contact_email is None and body.tax_id is None and body.address is None
