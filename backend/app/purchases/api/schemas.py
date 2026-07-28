import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.purchases.domain.entities import Purchase
from app.purchases.domain.value_objects import PurchasePaymentStatus, PurchaseStatus


class PurchaseLineItemSchema(BaseModel):
    line_number: int
    description: str
    quantity: Decimal
    unit_cost: Decimal
    line_total: Decimal
    product_id: uuid.UUID | None = None


class CreatePurchaseLineItemRequest(BaseModel):
    line_number: int
    description: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal
    product_id: uuid.UUID | None = None


class CreatePurchaseRequest(BaseModel):
    purchase_number: str = Field(min_length=1, max_length=100)
    vendor_id: uuid.UUID
    purchase_date: date
    due_date: date | None = None
    line_items: list[CreatePurchaseLineItemRequest] = Field(min_length=1)
    tax: Decimal | None = None
    notes: str | None = None


class RecordPurchasePaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0)


class PurchaseResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    purchase_number: str
    vendor_id: uuid.UUID
    purchase_date: date
    due_date: date | None
    line_items: list[PurchaseLineItemSchema]
    subtotal: Decimal
    tax: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    outstanding_amount: Decimal
    payment_status: PurchasePaymentStatus
    notes: str | None
    status: PurchaseStatus
    created_at: datetime

    @classmethod
    def from_domain(cls, purchase: Purchase) -> "PurchaseResponse":
        return cls(
            id=purchase.id,
            business_id=purchase.business_id,
            purchase_number=purchase.purchase_number,
            vendor_id=purchase.vendor_id,
            purchase_date=purchase.purchase_date,
            due_date=purchase.due_date,
            line_items=[
                PurchaseLineItemSchema(
                    line_number=item.line_number,
                    description=item.description,
                    quantity=item.quantity,
                    unit_cost=item.unit_cost.amount,
                    line_total=item.line_total.amount,
                    product_id=item.product_id,
                )
                for item in purchase.line_items
            ],
            subtotal=purchase.subtotal.amount,
            tax=purchase.tax.amount,
            total_amount=purchase.total_amount.amount,
            amount_paid=purchase.amount_paid.amount,
            outstanding_amount=purchase.outstanding_amount.amount,
            payment_status=purchase.payment_status,
            notes=purchase.notes,
            status=purchase.status,
            created_at=purchase.created_at,
        )


class PagedPurchasesResponse(BaseModel):
    items: list[PurchaseResponse]
    total: int
    offset: int
    limit: int
