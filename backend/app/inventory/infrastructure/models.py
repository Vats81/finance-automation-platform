import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.db.base import Base


class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    selling_price_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    purchase_cost_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    current_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    minimum_stock_level: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    reorder_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    unit_of_measurement: Mapped[str] = mapped_column(String(30), nullable=False, default="unit")
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
