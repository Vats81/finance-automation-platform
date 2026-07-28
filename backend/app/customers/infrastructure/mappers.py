from app.customers.domain.entities import Customer
from app.customers.domain.value_objects import CustomerAddress, CustomerEmailAddress, CustomerStatus
from app.customers.infrastructure.models import CustomerModel


def model_to_domain(model: CustomerModel) -> Customer:
    address = None
    if model.street and model.city and model.state and model.postal_code:
        address = CustomerAddress(
            street=model.street,
            city=model.city,
            state=model.state,
            postal_code=model.postal_code,
            country=model.country or "US",
        )

    return Customer(
        entity_id=model.id,
        business_id=model.business_id,
        name=model.name,
        phone=model.phone,
        email=CustomerEmailAddress(model.email) if model.email else None,
        address=address,
        gst_number=model.gst_number,
        status=CustomerStatus(model.status),
        created_at=model.created_at,
    )


def domain_to_model(customer: Customer) -> CustomerModel:
    return CustomerModel(
        id=customer.id,
        business_id=customer.business_id,
        name=customer.name,
        phone=customer.phone,
        email=str(customer.email) if customer.email else None,
        street=customer.address.street if customer.address else None,
        city=customer.address.city if customer.address else None,
        state=customer.address.state if customer.address else None,
        postal_code=customer.address.postal_code if customer.address else None,
        country=customer.address.country if customer.address else None,
        gst_number=customer.gst_number,
        status=customer.status.value,
        created_at=customer.created_at,
    )


def apply_domain_to_existing_model(customer: Customer, model: CustomerModel) -> None:
    model.name = customer.name
    model.phone = customer.phone
    model.email = str(customer.email) if customer.email else None
    model.street = customer.address.street if customer.address else None
    model.city = customer.address.city if customer.address else None
    model.state = customer.address.state if customer.address else None
    model.postal_code = customer.address.postal_code if customer.address else None
    model.country = customer.address.country if customer.address else None
    model.gst_number = customer.gst_number
    model.status = customer.status.value
