from app.vendors.domain.entities import Vendor
from app.vendors.domain.value_objects import Address, TaxId, VendorEmailAddress, VendorStatus
from app.vendors.infrastructure.models import VendorModel


def model_to_domain(model: VendorModel) -> Vendor:
    return Vendor(
        entity_id=model.id,
        legal_name=model.legal_name,
        contact_email=VendorEmailAddress(model.contact_email),
        tax_id=TaxId(model.tax_id),
        address=Address(
            street=model.street,
            city=model.city,
            state=model.state,
            postal_code=model.postal_code,
            country=model.country,
        ),
        status=VendorStatus(model.status),
        w9_document_reference=model.w9_document_reference,
        business_id=model.business_id,
        created_at=model.created_at,
    )


def domain_to_model(vendor: Vendor) -> VendorModel:
    return VendorModel(
        id=vendor.id,
        legal_name=vendor.legal_name,
        contact_email=str(vendor.contact_email),
        tax_id=vendor.tax_id.unmasked,
        street=vendor.address.street,
        city=vendor.address.city,
        state=vendor.address.state,
        postal_code=vendor.address.postal_code,
        country=vendor.address.country,
        status=vendor.status.value,
        w9_document_reference=vendor.w9_document_reference,
        business_id=vendor.business_id,
        created_at=vendor.created_at,
    )


def apply_domain_to_existing_model(vendor: Vendor, model: VendorModel) -> None:
    model.legal_name = vendor.legal_name
    model.contact_email = str(vendor.contact_email)
    model.street = vendor.address.street
    model.city = vendor.address.city
    model.state = vendor.address.state
    model.postal_code = vendor.address.postal_code
    model.country = vendor.address.country
    model.status = vendor.status.value
    model.w9_document_reference = vendor.w9_document_reference
