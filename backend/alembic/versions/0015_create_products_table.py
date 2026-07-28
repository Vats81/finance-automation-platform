"""create products table

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("selling_price_cents", sa.BigInteger(), nullable=False),
        sa.Column("purchase_cost_cents", sa.BigInteger(), nullable=False),
        sa.Column("current_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("minimum_stock_level", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("reorder_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("unit_of_measurement", sa.String(length=30), nullable=False, server_default="unit"),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
    )
    op.create_index(op.f("ix_products_business_id"), "products", ["business_id"])
    op.create_index(op.f("ix_products_sku"), "products", ["sku"])


def downgrade() -> None:
    op.drop_index(op.f("ix_products_sku"), table_name="products")
    op.drop_index(op.f("ix_products_business_id"), table_name="products")
    op.drop_table("products")
