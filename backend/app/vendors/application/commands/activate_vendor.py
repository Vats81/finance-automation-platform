import uuid
from dataclasses import dataclass

from app.vendors.application.ports import VendorsUnitOfWork
from app.vendors.domain.entities import Vendor
from app.vendors.domain.exceptions import VendorNotFoundException


@dataclass(frozen=True)
class ActivateVendorCommand:
    vendor_id: uuid.UUID


class ActivateVendorUseCase:
    """Enforces the "no activation without a W-9 on file" invariant, which
    lives in Vendor.activate() itself — this use case is a thin transaction
    wrapper around it.
    """

    def __init__(self, uow: VendorsUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: ActivateVendorCommand) -> Vendor:
        vendor = await self._uow.vendors.get_by_id(command.vendor_id)
        if vendor is None:
            raise VendorNotFoundException(f"Vendor {command.vendor_id} not found")

        vendor.activate()
        await self._uow.vendors.update(vendor)
        await self._uow.commit()
        return vendor
