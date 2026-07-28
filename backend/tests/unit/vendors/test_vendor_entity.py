import pytest

from app.vendors.domain.entities import Vendor
from app.vendors.domain.exceptions import VendorAlreadyActiveException, VendorMissingW9Exception
from app.vendors.domain.value_objects import Address, TaxId, VendorEmailAddress, VendorStatus


def make_address() -> Address:
    return Address(street="1 Main St", city="Springfield", state="IL", postal_code="62701")


def make_vendor() -> Vendor:
    vendor = Vendor.create(
        legal_name="Acme Supplies",
        contact_email=VendorEmailAddress("ap@acme.com"),
        tax_id=TaxId("12-3456789"),
        address=make_address(),
    )
    vendor.pull_domain_events()
    return vendor


def test_create_defaults_to_pending_review_and_records_event() -> None:
    vendor = Vendor.create(
        legal_name="Acme Supplies",
        contact_email=VendorEmailAddress("ap@acme.com"),
        tax_id=TaxId("12-3456789"),
        address=make_address(),
    )

    assert vendor.status == VendorStatus.PENDING_REVIEW
    events = vendor.pull_domain_events()
    assert [e.event_type for e in events] == ["VendorCreated"]


def test_activate_without_w9_raises() -> None:
    vendor = make_vendor()

    with pytest.raises(VendorMissingW9Exception):
        vendor.activate()


def test_activate_after_w9_upload_succeeds() -> None:
    vendor = make_vendor()
    vendor.record_w9_document("documents/w9/acme.pdf")
    vendor.pull_domain_events()

    vendor.activate()

    assert vendor.status == VendorStatus.ACTIVE
    assert vendor.is_active
    events = vendor.pull_domain_events()
    assert [e.event_type for e in events] == ["VendorActivated"]


def test_activate_twice_raises_already_active() -> None:
    vendor = make_vendor()
    vendor.record_w9_document("documents/w9/acme.pdf")
    vendor.activate()

    with pytest.raises(VendorAlreadyActiveException):
        vendor.activate()


def test_tax_id_is_masked_in_string_representation() -> None:
    tax_id = TaxId("12-3456789")

    assert str(tax_id) == "**-***6789"
    assert tax_id.unmasked == "12-3456789"


def test_update_details_only_records_event_when_something_changed() -> None:
    vendor = make_vendor()

    vendor.update_details(legal_name="Acme Supplies")  # unchanged
    assert vendor.pull_domain_events() == []

    vendor.update_details(legal_name="Acme Supplies Inc.")
    events = vendor.pull_domain_events()
    assert len(events) == 1
    assert events[0].changed_fields == ["legal_name"]
