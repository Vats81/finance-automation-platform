import uuid
from dataclasses import dataclass

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
    contact_email: str
    tax_id: str
    street: str
    city: str
    state: str
    postal_code: str
    country: str = "US"


class CreateBusinessVendorUseCase:
    def __init__(self, uow: VendorsUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: CreateBusinessVendorCommand) -> Vendor:
        vendor = Vendor.create(
            legal_name=command.legal_name,
            contact_email=VendorEmailAddress(command.contact_email),
            tax_id=TaxId(command.tax_id),
            address=Address(
                street=command.street,
                city=command.city,
                state=command.state,
                postal_code=command.postal_code,
                country=command.country,
            ),
            business_id=command.business_id,
        )
        self._uow.vendors.add(vendor)
        await self._uow.commit()
        return vendor
