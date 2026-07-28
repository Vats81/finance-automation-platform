import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.invoices.domain.entities import Invoice
from app.invoices.domain.value_objects import InvoiceStatus


class LineItemRequest(BaseModel):
    line_number: int = Field(ge=1)
    description: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(gt=0)


class SubmitInvoiceRequest(BaseModel):
    invoice_number: str = Field(min_length=1, max_length=100)
    vendor_id: uuid.UUID
    po_id: uuid.UUID
    line_items: list[LineItemRequest] = Field(min_length=1)


class LineItemResponse(BaseModel):
    line_number: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    invoice_number: str
    vendor_id: uuid.UUID
    po_id: uuid.UUID
    status: InvoiceStatus
    line_items: list[LineItemResponse]
    total_amount: Decimal
    document_reference: str | None
    match_discrepancies: list[str]
    created_at: datetime

    @classmethod
    def from_domain(cls, invoice: Invoice) -> "InvoiceResponse":
        return cls(
            id=invoice.id,
            invoice_number=invoice.invoice_number,
            vendor_id=invoice.vendor_id,
            po_id=invoice.po_id,
            status=invoice.status,
            line_items=[
                LineItemResponse(
                    line_number=item.line_number,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price.amount,
                    line_total=item.line_total.amount,
                )
                for item in invoice.line_items
            ],
            total_amount=invoice.total_amount.amount,
            document_reference=invoice.document_reference,
            match_discrepancies=invoice.match_discrepancies,
            created_at=invoice.created_at,
        )


class PagedInvoicesResponse(BaseModel):
    items: list[InvoiceResponse]
    total: int
    offset: int
    limit: int
