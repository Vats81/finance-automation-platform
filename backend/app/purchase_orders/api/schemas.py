import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.purchase_orders.domain.entities import PurchaseOrder
from app.purchase_orders.domain.value_objects import PurchaseOrderStatus


class LineItemRequest(BaseModel):
    line_number: int = Field(ge=1)
    description: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(gt=0)


class CreatePurchaseOrderRequest(BaseModel):
    vendor_id: uuid.UUID
    line_items: list[LineItemRequest] = Field(min_length=1)


class LineItemResponse(BaseModel):
    line_number: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class PurchaseOrderResponse(BaseModel):
    id: uuid.UUID
    po_number: str
    vendor_id: uuid.UUID
    status: PurchaseOrderStatus
    line_items: list[LineItemResponse]
    total_amount: Decimal
    created_at: datetime

    @classmethod
    def from_domain(cls, po: PurchaseOrder) -> "PurchaseOrderResponse":
        return cls(
            id=po.id,
            po_number=po.po_number,
            vendor_id=po.vendor_id,
            status=po.status,
            line_items=[
                LineItemResponse(
                    line_number=item.line_number,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price.amount,
                    line_total=item.line_total.amount,
                )
                for item in po.line_items
            ],
            total_amount=po.total_amount.amount,
            created_at=po.created_at,
        )


class PagedPurchaseOrdersResponse(BaseModel):
    items: list[PurchaseOrderResponse]
    total: int
    offset: int
    limit: int
