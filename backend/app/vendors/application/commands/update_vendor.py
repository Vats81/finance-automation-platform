import uuid
from dataclasses import dataclass

from app.vendors.application.ports import VendorsUnitOfWork
from app.vendors.domain.entities import Vendor
from app.vendors.domain.exceptions import VendorNotFoundException
from app.vendors.domain.value_objects import Address, VendorEmailAddress


@dataclass(frozen=True)
class UpdateVendorCommand:
    vendor_id: uuid.UUID
    legal_name: str | None = None
    contact_email: str | None = None
    street: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None


class UpdateVendorUseCase:
    def __init__(self, uow: VendorsUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: UpdateVendorCommand) -> Vendor:
        vendor = await self._uow.vendors.get_by_id(command.vendor_id)
        if vendor is None:
            raise VendorNotFoundException(f"Vendor {command.vendor_id} not found")

        address = None
        if any([command.street, command.city, command.state, command.postal_code]):
            address = Address(
                street=command.street or vendor.address.street,
                city=command.city or vendor.address.city,
                state=command.state or vendor.address.state,
                postal_code=command.postal_code or vendor.address.postal_code,
                country=command.country or vendor.address.country,
            )

        vendor.update_details(
            legal_name=command.legal_name,
            contact_email=VendorEmailAddress(command.contact_email) if command.contact_email else None,
            address=address,
        )
        await self._uow.vendors.update(vendor)
        await self._uow.commit()
        return vendor
