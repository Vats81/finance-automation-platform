import uuid
from dataclasses import dataclass
from typing import BinaryIO

from app.invoices.application.ports import InvoicesUnitOfWork
from app.invoices.domain.entities import Invoice
from app.invoices.domain.exceptions import InvoiceNotFoundException
from app.shared.application.ports import IFileStorage


@dataclass(frozen=True)
class AttachDocumentCommand:
    invoice_id: uuid.UUID
    filename: str
    content: BinaryIO
    content_type: str


class AttachDocumentUseCase:
    """Uploads the source invoice document (PDF/scan) to blob storage and
    records the reference — mirrors vendors' UploadW9DocumentUseCase. Kept
    separate from SubmitInvoiceUseCase so submission stays a simple JSON
    call; the document can be attached before or after submission.
    """

    def __init__(self, uow: InvoicesUnitOfWork, file_storage: IFileStorage, container_name: str) -> None:
        self._uow = uow
        self._file_storage = file_storage
        self._container_name = container_name

    async def execute(self, command: AttachDocumentCommand) -> Invoice:
        invoice = await self._uow.invoices.get_by_id(command.invoice_id)
        if invoice is None:
            raise InvoiceNotFoundException(f"Invoice {command.invoice_id} not found")

        blob_name = f"invoices/{invoice.id}/document/{command.filename}"
        reference = await self._file_storage.upload(
            container=self._container_name,
            blob_name=blob_name,
            data=command.content,
            content_type=command.content_type,
        )

        invoice.attach_document(reference)
        await self._uow.invoices.update(invoice)
        await self._uow.commit()
        return invoice
