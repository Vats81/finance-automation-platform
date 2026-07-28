import uuid
from dataclasses import dataclass
from typing import BinaryIO

from app.shared.application.ports import IFileStorage
from app.vendors.application.ports import VendorsUnitOfWork
from app.vendors.domain.entities import Vendor
from app.vendors.domain.exceptions import VendorNotFoundException


@dataclass(frozen=True)
class UploadW9DocumentCommand:
    vendor_id: uuid.UUID
    filename: str
    content: BinaryIO
    content_type: str


class UploadW9DocumentUseCase:
    """Uploads the W-9 to blob storage via the IFileStorage port, then
    records the resulting reference on the Vendor aggregate — this is what
    satisfies the "no activation without a W-9 on file" invariant in
    Vendor.activate(). The use case never imports Azure/Azurite directly.
    """

    def __init__(self, uow: VendorsUnitOfWork, file_storage: IFileStorage, container_name: str) -> None:
        self._uow = uow
        self._file_storage = file_storage
        self._container_name = container_name

    async def execute(self, command: UploadW9DocumentCommand) -> Vendor:
        vendor = await self._uow.vendors.get_by_id(command.vendor_id)
        if vendor is None:
            raise VendorNotFoundException(f"Vendor {command.vendor_id} not found")

        blob_name = f"vendors/{vendor.id}/w9/{command.filename}"
        reference = await self._file_storage.upload(
            container=self._container_name,
            blob_name=blob_name,
            data=command.content,
            content_type=command.content_type,
        )

        vendor.record_w9_document(reference)
        await self._uow.vendors.update(vendor)
        await self._uow.commit()
        return vendor
