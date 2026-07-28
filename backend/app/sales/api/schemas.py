import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.sales.domain.entities import Sale
from app.sales.domain.value_objects import SalePaymentStatus, SaleStatus


class SaleLineItemSchema(BaseModel):
    line_number: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class CreateSaleLineItemRequest(BaseModel):
    line_number: int
    description: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal


class CreateSaleRequest(BaseModel):
    invoice_number: str = Field(min_length=1, max_length=100)
    invoice_date: date
    due_date: date | None = None
    customer_id: uuid.UUID | None = None
    line_items: list[CreateSaleLineItemRequest] = Field(min_length=1)
    discount: Decimal | None = None
    tax: Decimal | None = None
    notes: str | None = None


class RecordSalePaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0)


class SaleResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    invoice_number: str
    customer_id: uuid.UUID | None
    invoice_date: date
    due_date: date | None
    line_items: list[SaleLineItemSchema]
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total_amount: Decimal
    amount_received: Decimal
    outstanding_amount: Decimal
    payment_status: SalePaymentStatus
    notes: str | None
    status: SaleStatus
    created_at: datetime

    @classmethod
    def from_domain(cls, sale: Sale) -> "SaleResponse":
        return cls(
            id=sale.id,
            business_id=sale.business_id,
            invoice_number=sale.invoice_number,
            customer_id=sale.customer_id,
            invoice_date=sale.invoice_date,
            due_date=sale.due_date,
            line_items=[
                SaleLineItemSchema(
                    line_number=item.line_number,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price.amount,
                    line_total=item.line_total.amount,
                )
                for item in sale.line_items
            ],
            subtotal=sale.subtotal.amount,
            discount=sale.discount.amount,
            tax=sale.tax.amount,
            total_amount=sale.total_amount.amount,
            amount_received=sale.amount_received.amount,
            outstanding_amount=sale.outstanding_amount.amount,
            payment_status=sale.payment_status,
            notes=sale.notes,
            status=sale.status,
            created_at=sale.created_at,
        )


class PagedSalesResponse(BaseModel):
    items: list[SaleResponse]
    total: int
    offset: int
    limit: int
