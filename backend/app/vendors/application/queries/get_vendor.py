import uuid
from dataclasses import dataclass

from app.vendors.application.ports import VendorsUnitOfWork
from app.vendors.domain.entities import Vendor
from app.vendors.domain.exceptions import VendorNotFoundException


@dataclass(frozen=True)
class GetVendorQuery:
    vendor_id: uuid.UUID


class GetVendorUseCase:
    def __init__(self, uow: VendorsUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: GetVendorQuery) -> Vendor:
        vendor = await self._uow.vendors.get_by_id(query.vendor_id)
        if vendor is None:
            raise VendorNotFoundException(f"Vendor {query.vendor_id} not found")
        return vendor
