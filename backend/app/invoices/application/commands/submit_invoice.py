import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.invoices.application.ports import InvoicesUnitOfWork
from app.invoices.domain.entities import Invoice
from app.invoices.domain.value_objects import InvoiceLineItem
from app.shared.domain.value_objects import Money


@dataclass(frozen=True)
class SubmitInvoiceLineItemInput:
    line_number: int
    description: str
    quantity: Decimal
    unit_price: Decimal


@dataclass(frozen=True)
class SubmitInvoiceCommand:
    invoice_number: str
    vendor_id: uuid.UUID
    po_id: uuid.UUID
    line_items: list[SubmitInvoiceLineItemInput]


class SubmitInvoiceUseCase:
    """Records the invoice as SUBMITTED. The InvoiceSubmitted event this
    raises is what triggers async document processing + matching — see
    invoices/application/event_handlers and workers/tasks/ocr_tasks.py —
    via the outbox relay rather than a direct enqueue, so the pipeline
    survives a crash between commit and enqueue.
    """

    def __init__(self, uow: InvoicesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: SubmitInvoiceCommand) -> Invoice:
        line_items = [
            InvoiceLineItem(
                line_number=item.line_number,
                description=item.description,
                quantity=item.quantity,
                unit_price=Money(amount=item.unit_price),
            )
            for item in command.line_items
        ]
        invoice = Invoice.submit(
            invoice_number=command.invoice_number,
            vendor_id=command.vendor_id,
            po_id=command.po_id,
            line_items=line_items,
        )
        self._uow.invoices.add(invoice)
        await self._uow.commit()
        return invoice
