"""The seller details a GST invoice prints: GSTIN, address, state, PIN code, phone and UPI ID."""

import uuid

import pytest

from app.business.application.commands.complete_onboarding import (
    CompleteOnboardingCommand,
    CompleteOnboardingUseCase,
)
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.shared.domain.exceptions import ValidationException
from app.shared.domain.gst import (
    GST_STATES,
    clean_gstin,
    clean_pincode,
    clean_state_code,
    clean_upi_id,
    gstin_check_character,
)
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

VALID = ["27AAPFU0939F1ZV", "07AAGFF2194N1Z1", "29AAACH7409R1ZX"]


@pytest.mark.parametrize("gstin", VALID)
def test_a_real_format_gstin_is_accepted_and_tidied(gstin: str) -> None:
    assert clean_gstin(f"  {gstin.lower()} ") == gstin
    assert gstin_check_character(gstin[:14]) == gstin[14]


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "27AAPFU0939F1Z",  # too short
        "27AAPFU0939F1ZVV",  # too long
        "27AAPFU0939F1ZW",  # wrong check character
        "27AAPFU0938F1ZV",  # a digit changed
        "00AAPFU0939F1ZV",  # not a state
        "27AAPFU0939F1XV",  # 14th character must be Z
    ],
)
def test_a_mistyped_gstin_is_refused(bad: str) -> None:
    with pytest.raises(ValidationException):
        clean_gstin(bad)


def test_the_state_pin_and_upi_cleaners() -> None:
    assert clean_state_code(" 27 ") == "27" and "27" in GST_STATES
    assert clean_pincode("560001") == "560001"
    assert clean_upi_id(" shop.name@okhdfcbank ") == "shop.name@okhdfcbank"
    for bad in ("00", "99x", "", "1"):
        with pytest.raises(ValidationException):
            clean_state_code(bad)
    for bad in ("56001", "0560001", "5600011", "abcdef"):
        with pytest.raises(ValidationException):
            clean_pincode(bad)
    for bad in ("nobank", "@bank", "name@", "na me@bank"):
        with pytest.raises(ValidationException):
            clean_upi_id(bad)


async def _business(uow: FakeUnitOfWork) -> uuid.UUID:
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Sharma Stores")
    )
    return business.id


async def test_the_invoice_details_are_saved_and_a_gstin_fixes_the_state() -> None:
    uow = FakeUnitOfWork()
    business_id = await _business(uow)

    saved = await CompleteOnboardingUseCase(uow).execute(
        CompleteOnboardingCommand(
            business_id=business_id,
            gstin="27aapfu0939f1zv",
            address_line="12 MG Road",
            city="Pune",
            pincode="411001",
            phone="+91 98765 43210",
            upi_id="sharma@okhdfcbank",
        )
    )

    assert saved.gstin == "27AAPFU0939F1ZV"
    assert saved.state_code == "27"  # taken from the GSTIN
    assert saved.gst_registered is True  # having a GSTIN means GST-registered
    assert (saved.address_line, saved.city, saved.pincode) == ("12 MG Road", "Pune", "411001")
    assert (saved.phone, saved.upi_id) == ("+91 98765 43210", "sharma@okhdfcbank")


async def test_a_state_that_contradicts_the_gstin_is_refused() -> None:
    uow = FakeUnitOfWork()
    business_id = await _business(uow)

    with pytest.raises(ValidationException):
        await CompleteOnboardingUseCase(uow).execute(
            CompleteOnboardingCommand(business_id=business_id, gstin="27AAPFU0939F1ZV", state_code="29")
        )


async def test_a_business_without_a_gstin_can_still_set_its_state() -> None:
    uow = FakeUnitOfWork()
    business_id = await _business(uow)

    saved = await CompleteOnboardingUseCase(uow).execute(
        CompleteOnboardingCommand(business_id=business_id, state_code="29")
    )

    assert saved.state_code == "29" and saved.gstin is None and saved.gst_registered is False


async def test_only_what_is_given_changes_and_an_empty_value_clears_a_field() -> None:
    uow = FakeUnitOfWork()
    business_id = await _business(uow)
    use_case = CompleteOnboardingUseCase(uow)
    await use_case.execute(
        CompleteOnboardingCommand(business_id=business_id, city="Pune", phone="12345", upi_id="a.b@upi")
    )

    after = await use_case.execute(
        CompleteOnboardingCommand(business_id=business_id, city="Mumbai", phone="")
    )

    assert after.city == "Mumbai"  # changed
    assert after.phone is None  # cleared
    assert after.upi_id == "a.b@upi"  # untouched


async def test_a_bad_value_changes_nothing() -> None:
    uow = FakeUnitOfWork()
    business_id = await _business(uow)

    with pytest.raises(ValidationException):
        await CompleteOnboardingUseCase(uow).execute(
            CompleteOnboardingCommand(business_id=business_id, city="Pune", pincode="123")
        )

    stored = await uow.businesses.get_by_id(business_id)
    assert stored is not None and stored.pincode is None


async def test_an_empty_state_in_the_form_does_not_erase_the_state_a_gstin_fixes() -> None:
    uow = FakeUnitOfWork()
    business_id = await _business(uow)
    use_case = CompleteOnboardingUseCase(uow)
    await use_case.execute(CompleteOnboardingCommand(business_id=business_id, gstin="27AAPFU0939F1ZV"))

    after = await use_case.execute(CompleteOnboardingCommand(business_id=business_id, state_code=""))

    assert after.state_code == "27"
