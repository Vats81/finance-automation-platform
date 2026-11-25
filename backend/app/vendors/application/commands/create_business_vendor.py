import uuid
from dataclasses import dataclass

from app.shared.domain.exceptions import ValidationException
from app.vendors.application.ports import VendorsUnitOfWork
from app.vendors.domain.entities import Vendor
from app.vendors.domain.value_objects import Address, TaxId, VendorEmailAddress


@dataclass(frozen=True)
class CreateBusinessVendorCommand:
    """Same shape as CreateVendorCommand plus business_id — kept as a
    separate command/use case (rather than adding an optional business_id
    to the existing one) so the AP-automation product's CreateVendorUseCase
    and its tests are untouched.
    """

    business_id: uuid.UUID
    legal_name: str
    contact_email: str | None = None
    tax_id: str | None = None
    street: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str = "US"


class CreateBusinessVendorUseCase:
    """Only the name is required: a shop often knows its supplier by name and nothing else. Anything that is
    given is still checked, and an address is the whole of it or none of it.
    """

    def __init__(self, uow: VendorsUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: CreateBusinessVendorCommand) -> Vendor:
        name = " ".join(command.legal_name.split())
        if not name:
            raise ValidationException("Enter the supplier's name.")
        email = (command.contact_email or "").strip()
        tax_id = "".join((command.tax_id or "").split()).upper()
        address_parts = [
            (part or "").strip()
            for part in (command.street, command.city, command.state, command.postal_code)
        ]
        if any(address_parts) and not all(address_parts):
            raise ValidationException(
                "Fill in the whole address (street, city, state and postal code) or leave it empty."
            )
        street, city, state, postal_code = address_parts
        vendor = Vendor.create(
            legal_name=name,
            contact_email=VendorEmailAddress(email) if email else VendorEmailAddress.not_provided(),
            tax_id=TaxId(tax_id) if tax_id else TaxId.not_provided(),
            address=Address(
                street=street, city=city, state=state, postal_code=postal_code, country=command.country
            )
            if any(address_parts)
            else Address.not_provided(),
            business_id=command.business_id,
        )
        self._uow.vendors.add(vendor)
        await self._uow.commit()
        return vendor
