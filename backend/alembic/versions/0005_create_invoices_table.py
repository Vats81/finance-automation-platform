"""create invoices table

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("invoice_number", sa.String(length=100), nullable=False),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("po_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("line_items", postgresql.JSONB, nullable=False),
        sa.Column("document_reference", sa.String(length=500), nullable=True),
        sa.Column("match_discrepancies", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoices")),
    )
    op.create_index(op.f("ix_invoices_invoice_number"), "invoices", ["invoice_number"])
    op.create_index(op.f("ix_invoices_vendor_id"), "invoices", ["vendor_id"])
    op.create_index(op.f("ix_invoices_po_id"), "invoices", ["po_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_invoices_po_id"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_vendor_id"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_invoice_number"), table_name="invoices")
    op.drop_table("invoices")
