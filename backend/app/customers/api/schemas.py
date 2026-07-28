import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.customers.domain.entities import Customer
from app.customers.domain.value_objects import CustomerStatus


class CustomerAddressSchema(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    country: str = "US"


class CreateCustomerRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str | None = None
    email: EmailStr | None = None
    address: CustomerAddressSchema | None = None
    gst_number: str | None = None


class UpdateCustomerRequest(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: CustomerAddressSchema | None = None
    gst_number: str | None = None


class CustomerResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    phone: str | None
    email: str | None
    address: CustomerAddressSchema | None
    gst_number: str | None
    status: CustomerStatus
    created_at: datetime

    @classmethod
    def from_domain(cls, customer: Customer) -> "CustomerResponse":
        return cls(
            id=customer.id,
            business_id=customer.business_id,
            name=customer.name,
            phone=customer.phone,
            email=str(customer.email) if customer.email else None,
            address=CustomerAddressSchema(
                street=customer.address.street,
                city=customer.address.city,
                state=customer.address.state,
                postal_code=customer.address.postal_code,
                country=customer.address.country,
            )
            if customer.address
            else None,
            gst_number=customer.gst_number,
            status=customer.status,
            created_at=customer.created_at,
        )


class PagedCustomersResponse(BaseModel):
    items: list[CustomerResponse]
    total: int
    offset: int
    limit: int
