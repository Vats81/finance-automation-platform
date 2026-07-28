import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.inventory.domain.entities import Product
from app.inventory.domain.value_objects import ProductStatus


class CreateProductRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sku: str = Field(min_length=1, max_length=100)
    selling_price: Decimal = Field(ge=0)
    purchase_cost: Decimal = Field(ge=0)
    category: str | None = None
    current_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    minimum_stock_level: Decimal = Field(default=Decimal("0"), ge=0)
    reorder_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    unit_of_measurement: str = "unit"
    vendor_id: uuid.UUID | None = None


class UpdateProductRequest(BaseModel):
    name: str | None = None
    category: str | None = None
    selling_price: Decimal | None = None
    purchase_cost: Decimal | None = None
    minimum_stock_level: Decimal | None = None
    reorder_quantity: Decimal | None = None


class AdjustStockRequest(BaseModel):
    delta: Decimal
    reason: str = Field(min_length=1, max_length=255)


class ProductResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    sku: str
    category: str | None
    selling_price: Decimal
    purchase_cost: Decimal
    current_quantity: Decimal
    minimum_stock_level: Decimal
    reorder_quantity: Decimal
    unit_of_measurement: str
    vendor_id: uuid.UUID | None
    stock_value: Decimal
    is_low_stock: bool
    is_out_of_stock: bool
    status: ProductStatus
    created_at: datetime

    @classmethod
    def from_domain(cls, product: Product) -> "ProductResponse":
        return cls(
            id=product.id,
            business_id=product.business_id,
            name=product.name,
            sku=product.sku,
            category=product.category,
            selling_price=product.selling_price.amount,
            purchase_cost=product.purchase_cost.amount,
            current_quantity=product.current_quantity,
            minimum_stock_level=product.minimum_stock_level,
            reorder_quantity=product.reorder_quantity,
            unit_of_measurement=product.unit_of_measurement,
            vendor_id=product.vendor_id,
            stock_value=product.stock_value.amount,
            is_low_stock=product.is_low_stock,
            is_out_of_stock=product.is_out_of_stock,
            status=product.status,
            created_at=product.created_at,
        )


class PagedProductsResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    offset: int
    limit: int
