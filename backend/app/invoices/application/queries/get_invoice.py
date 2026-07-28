import uuid
from dataclasses import dataclass

from app.invoices.application.ports import InvoicesUnitOfWork
from app.invoices.domain.entities import Invoice
from app.invoices.domain.exceptions import InvoiceNotFoundException


@dataclass(frozen=True)
class GetInvoiceQuery:
    invoice_id: uuid.UUID


class GetInvoiceUseCase:
    def __init__(self, uow: InvoicesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: GetInvoiceQuery) -> Invoice:
        invoice = await self._uow.invoices.get_by_id(query.invoice_id)
        if invoice is None:
            raise InvoiceNotFoundException(f"Invoice {query.invoice_id} not found")
        return invoice
