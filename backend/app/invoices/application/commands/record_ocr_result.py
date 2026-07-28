import uuid
from dataclasses import dataclass

from app.invoices.application.ports import InvoicesUnitOfWork
from app.invoices.domain.entities import Invoice
from app.invoices.domain.exceptions import InvoiceNotFoundException
from app.invoices.domain.matching.two_way_match import TwoWayMatchService
from app.invoices.infrastructure.document_processing_client import SimulatedDocumentProcessingClient
from app.purchase_orders.domain.exceptions import PurchaseOrderNotFoundException


@dataclass(frozen=True)
class RecordOcrResultCommand:
    invoice_id: uuid.UUID


class RecordOcrResultUseCase:
    """Invoked by workers/tasks/ocr_tasks.py after InvoiceSubmitted is
    relayed from the outbox. Runs the (simulated) document processing pass,
    then immediately performs 2-way matching against the referenced
    PurchaseOrder and transitions the invoice to MATCHED or MATCH_EXCEPTION.
    Both aggregates (Invoice, PurchaseOrder) are loaded read-only for
    matching — only the Invoice is mutated/persisted here.
    """

    def __init__(
        self,
        uow: InvoicesUnitOfWork,
        document_processing_client: SimulatedDocumentProcessingClient,
    ) -> None:
        self._uow = uow
        self._document_processing_client = document_processing_client

    async def execute(self, command: RecordOcrResultCommand) -> Invoice:
        invoice = await self._uow.invoices.get_by_id(command.invoice_id)
        if invoice is None:
            raise InvoiceNotFoundException(f"Invoice {command.invoice_id} not found")

        await self._document_processing_client.process(document_reference=invoice.document_reference)

        purchase_order = await self._uow.purchase_orders.get_by_id(invoice.po_id)
        if purchase_order is None:
            raise PurchaseOrderNotFoundException(f"PurchaseOrder {invoice.po_id} not found")

        result = TwoWayMatchService.match(invoice, purchase_order)
        if result.is_matched:
            invoice.mark_matched()
        else:
            invoice.mark_match_exception(result.discrepancies)

        await self._uow.invoices.update(invoice)
        await self._uow.commit()
        return invoice
