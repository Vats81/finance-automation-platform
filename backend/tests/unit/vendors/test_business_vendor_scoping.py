import uuid

import pytest

from app.vendors.application.commands.create_business_vendor import (
    CreateBusinessVendorCommand,
    CreateBusinessVendorUseCase,
)
from app.vendors.application.commands.create_vendor import CreateVendorCommand, CreateVendorUseCase
from app.vendors.application.commands.update_business_vendor import (
    UpdateBusinessVendorCommand,
    UpdateBusinessVendorUseCase,
)
from app.vendors.domain.exceptions import VendorNotFoundException
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


def vendor_command(**overrides) -> dict:
    base = dict(
        legal_name="Acme Supplies",
        contact_email="ap@acme.com",
        tax_id="12-3456789",
        street="1 Main St",
        city="Springfield",
        state="IL",
        postal_code="62701",
    )
    base.update(overrides)
    return base


async def test_create_business_vendor_sets_business_id() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    vendor = await CreateBusinessVendorUseCase(uow).execute(
        CreateBusinessVendorCommand(business_id=business_id, **vendor_command())
    )

    assert vendor.business_id == business_id


async def test_ap_automation_vendor_creation_leaves_business_id_none() -> None:
    """The existing AP-automation CreateVendorUseCase must be completely
    unaffected by the retrofit — proves the additive-only claim.
    """
    uow = FakeUnitOfWork()

    vendor = await CreateVendorUseCase(uow).execute(CreateVendorCommand(**vendor_command()))

    assert vendor.business_id is None


async def test_get_by_id_for_business_is_isolated_across_tenants() -> None:
    uow = FakeUnitOfWork()
    business_a = uuid.uuid4()
    business_b = uuid.uuid4()

    vendor = await CreateBusinessVendorUseCase(uow).execute(
        CreateBusinessVendorCommand(business_id=business_a, **vendor_command())
    )

    found_for_owner = await uow.vendors.get_by_id_for_business(vendor.id, business_a)
    found_for_other = await uow.vendors.get_by_id_for_business(vendor.id, business_b)

    assert found_for_owner is not None
    assert found_for_other is None


async def test_get_by_id_for_business_never_returns_an_ap_automation_vendor() -> None:
    """An AP-automation vendor (business_id=None) must never be reachable
    through the business-scoped lookup, even by a real business_id.
    """
    uow = FakeUnitOfWork()
    ap_vendor = await CreateVendorUseCase(uow).execute(CreateVendorCommand(**vendor_command()))

    result = await uow.vendors.get_by_id_for_business(ap_vendor.id, uuid.uuid4())

    assert result is None


async def test_list_for_business_only_returns_that_businesss_vendors() -> None:
    uow = FakeUnitOfWork()
    business_a = uuid.uuid4()
    business_b = uuid.uuid4()

    await CreateBusinessVendorUseCase(uow).execute(
        CreateBusinessVendorCommand(business_id=business_a, **vendor_command(legal_name="A Corp"))
    )
    await CreateBusinessVendorUseCase(uow).execute(
        CreateBusinessVendorCommand(business_id=business_b, **vendor_command(legal_name="B Corp"))
    )
    await CreateVendorUseCase(uow).execute(
        CreateVendorCommand(**vendor_command(legal_name="Legacy AP Vendor"))
    )

    vendors_a, total_a = await uow.vendors.list_for_business(business_a)

    assert total_a == 1
    assert vendors_a[0].legal_name == "A Corp"


async def test_update_business_vendor_cannot_touch_another_businesss_vendor() -> None:
    uow = FakeUnitOfWork()
    business_a = uuid.uuid4()
    business_b = uuid.uuid4()

    vendor = await CreateBusinessVendorUseCase(uow).execute(
        CreateBusinessVendorCommand(business_id=business_a, **vendor_command())
    )

    with pytest.raises(VendorNotFoundException):
        await UpdateBusinessVendorUseCase(uow).execute(
            UpdateBusinessVendorCommand(business_id=business_b, vendor_id=vendor.id, legal_name="Hijacked")
        )
