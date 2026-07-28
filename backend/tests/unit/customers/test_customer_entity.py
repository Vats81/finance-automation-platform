import uuid

from app.customers.domain.entities import Customer
from app.customers.domain.value_objects import CustomerAddress, CustomerEmailAddress, CustomerStatus


def make_address() -> CustomerAddress:
    return CustomerAddress(street="1 Main St", city="Springfield", state="IL", postal_code="62701")


def test_create_defaults_to_active_and_records_event() -> None:
    business_id = uuid.uuid4()

    customer = Customer.create(business_id=business_id, name="Jane's Diner")

    assert customer.business_id == business_id
    assert customer.status == CustomerStatus.ACTIVE
    assert customer.is_active
    events = customer.pull_domain_events()
    assert [e.event_type for e in events] == ["CustomerCreated"]


def test_update_details_only_records_event_when_something_changed() -> None:
    customer = Customer.create(business_id=uuid.uuid4(), name="Jane's Diner")
    customer.pull_domain_events()

    customer.update_details(name="Jane's Diner")  # unchanged
    assert customer.pull_domain_events() == []

    customer.update_details(name="Jane's Diner LLC", email=CustomerEmailAddress("jane@example.com"))
    events = customer.pull_domain_events()
    assert len(events) == 1
    assert set(events[0].changed_fields) == {"name", "email"}


def test_deactivate_then_reactivate() -> None:
    customer = Customer.create(business_id=uuid.uuid4(), name="Jane's Diner", address=make_address())
    customer.pull_domain_events()

    customer.deactivate()
    assert customer.status == CustomerStatus.INACTIVE
    assert customer.is_active is False
    events = customer.pull_domain_events()
    assert [e.event_type for e in events] == ["CustomerDeactivated"]

    customer.reactivate()
    assert customer.is_active is True
