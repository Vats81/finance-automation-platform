"""private links for sharing an invoice PDF with a customer

Revision ID: 0035
Revises: 0034
Create Date: 2026-11-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0035"
down_revision: Union[str, None] = "0034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoice_share_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("token_hash", name="uq_invoice_share_links_token_hash"),
    )
    op.create_index("ix_invoice_share_links_business_id", "invoice_share_links", ["business_id"])
    op.create_index("ix_invoice_share_links_sale_id", "invoice_share_links", ["sale_id"])


def downgrade() -> None:
    op.drop_index("ix_invoice_share_links_sale_id", table_name="invoice_share_links")
    op.drop_index("ix_invoice_share_links_business_id", table_name="invoice_share_links")
    op.drop_table("invoice_share_links")
