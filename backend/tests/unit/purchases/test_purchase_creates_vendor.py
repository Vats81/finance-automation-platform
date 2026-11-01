"""A supplier named on a purchase shows up on the Vendors page, once, without the AP paperwork."""

import uuid
from datetime import date
from decimal import Decimal

from app.purchases.application.commands.create_purchase import (
    CreatePurchaseCommand,
    CreatePurchaseLineItemInput,
    CreatePurchaseUseCase,
)
from app.vendors.application.commands.create_business_vendor import (
    CreateBusinessVendorCommand,
    CreateBusinessVendorUseCase,
)
from app.vendors.domain.value_objects import TaxId, VendorEmailAddress
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

BUSINESS = uuid.uuid4()


def _purchase(number: str, **overrides: object) -> CreatePurchaseCommand:
    fields: dict = dict(
        business_id=BUSINESS,
        purchase_number=number,
        vendor_id=None,
        vendor_name=None,
        purchase_date=date(2026, 10, 3),
        line_items=[
            CreatePurchaseLineItemInput(
                line_number=1, description="Flour", quantity=Decimal("2"), unit_cost=Decimal("10")
            )
        ],
    )
    fields.update(overrides)
    return CreatePurchaseCommand(**fields)


async def _vendors(uow: FakeUnitOfWork, business_id: uuid.UUID = BUSINESS) -> list:
    return (await uow.vendors.list_for_business(business_id, offset=0, limit=100))[0]


async def test_a_typed_supplier_becomes_a_vendor_linked_to_the_purchase() -> None:
    uow = FakeUnitOfWork()

    purchase = await CreatePurchaseUseCase(uow).execute(_purchase("P-1", vendor_name="Sunrise Flour Mills"))

    (vendor,) = await _vendors(uow)
    assert vendor.legal_name == "Sunrise Flour Mills" and vendor.business_id == BUSINESS
    assert purchase.vendor_id == vendor.id
    assert purchase.vendor_name is None  # a linked purchase names its supplier through the vendor


async def test_the_same_supplier_is_reused_whatever_the_capitals_or_spacing() -> None:
    uow = FakeUnitOfWork()
    use_case = CreatePurchaseUseCase(uow)

    first = await use_case.execute(_purchase("P-1", vendor_name="Sunrise Flour Mills"))
    second = await use_case.execute(_purchase("P-2", vendor_name="  sunrise   FLOUR mills "))

    assert len(await _vendors(uow)) == 1
    assert first.vendor_id == second.vendor_id


async def test_a_vendor_already_saved_with_full_details_is_reused_not_duplicated() -> None:
    uow = FakeUnitOfWork()
    saved = await CreateBusinessVendorUseCase(uow).execute(
        CreateBusinessVendorCommand(
            business_id=BUSINESS,
            legal_name="Sunrise Flour Mills",
            contact_email="orders@sunrise.example.com",
            tax_id="12-3456789",
            street="1 Mill Road",
            city="Austin",
            state="TX",
            postal_code="73301",
        )
    )

    purchase = await CreatePurchaseUseCase(uow).execute(_purchase("P-1", vendor_name="sunrise flour mills"))

    assert purchase.vendor_id == saved.id and len(await _vendors(uow)) == 1


async def test_a_chosen_vendor_wins_and_a_missing_name_still_needs_one() -> None:
    import pytest

    from app.shared.domain.exceptions import ValidationException

    uow = FakeUnitOfWork()
    chosen = uuid.uuid4()
    use_case = CreatePurchaseUseCase(uow)

    with_id = await use_case.execute(_purchase("P-1", vendor_id=chosen, vendor_name="Ignored Name"))
    assert (
        with_id.vendor_id == chosen and await _vendors(uow) == []
    )  # nothing is invented for a chosen vendor

    for nameless in (_purchase("P-2"), _purchase("P-3", vendor_name="   ")):
        with pytest.raises(ValidationException):  # a purchase always needs a vendor, as before
            await use_case.execute(nameless)
    assert await _vendors(uow) == []


async def test_suppliers_are_kept_apart_between_businesses() -> None:
    uow = FakeUnitOfWork()
    other = uuid.uuid4()

    mine = await CreatePurchaseUseCase(uow).execute(_purchase("P-1", vendor_name="Shared Name"))
    theirs = await CreatePurchaseUseCase(uow).execute(
        _purchase("P-1", vendor_name="Shared Name", business_id=other)
    )

    assert mine.vendor_id != theirs.vendor_id
    assert len(await _vendors(uow, BUSINESS)) == 1 and len(await _vendors(uow, other)) == 1


async def test_a_name_only_vendor_has_no_made_up_contact_details() -> None:
    uow = FakeUnitOfWork()
    await CreatePurchaseUseCase(uow).execute(_purchase("P-1", vendor_name="Sunrise Flour Mills"))
    (vendor,) = await _vendors(uow)

    assert str(vendor.contact_email) == "" and vendor.tax_id.masked() == "" and vendor.address.street == ""


def test_real_input_is_still_validated_strictly() -> None:
    import pytest

    from app.shared.domain.exceptions import ValidationException

    with pytest.raises(ValidationException):
        VendorEmailAddress("")
    with pytest.raises(ValidationException):
        TaxId("")
