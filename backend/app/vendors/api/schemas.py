import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.vendors.domain.entities import Vendor
from app.vendors.domain.value_objects import VendorStatus


class AddressSchema(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    country: str = "US"


class CreateVendorRequest(BaseModel):
    legal_name: str = Field(min_length=1, max_length=255)
    contact_email: EmailStr
    tax_id: str = Field(description="EIN, format ##-#######")
    address: AddressSchema


class UpdateVendorRequest(BaseModel):
    legal_name: str | None = None
    contact_email: EmailStr | None = None
    address: AddressSchema | None = None


class VendorResponse(BaseModel):
    id: uuid.UUID
    legal_name: str
    contact_email: str
    tax_id_masked: str
    address: AddressSchema
    status: VendorStatus
    has_w9_on_file: bool
    created_at: datetime

    @classmethod
    def from_domain(cls, vendor: Vendor) -> "VendorResponse":
        return cls(
            id=vendor.id,
            legal_name=vendor.legal_name,
            contact_email=str(vendor.contact_email),
            tax_id_masked=vendor.tax_id.masked(),
            address=AddressSchema(
                street=vendor.address.street,
                city=vendor.address.city,
                state=vendor.address.state,
                postal_code=vendor.address.postal_code,
                country=vendor.address.country,
            ),
            status=vendor.status,
            has_w9_on_file=vendor.w9_document_reference is not None,
            created_at=vendor.created_at,
        )


class PagedVendorsResponse(BaseModel):
    items: list[VendorResponse]
    total: int
    offset: int
    limit: int
