"""create businesses table

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "businesses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("business_type", sa.String(length=100), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="USD"),
        sa.Column("financial_year_start_month", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("gst_registered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("business_size", sa.String(length=50), nullable=True),
        sa.Column("number_of_branches", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("whatsapp_number", sa.String(length=32), nullable=True),
        sa.Column("contact_email", sa.String(length=320), nullable=True),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_businesses")),
    )
    op.create_index(op.f("ix_businesses_owner_user_id"), "businesses", ["owner_user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_businesses_owner_user_id"), table_name="businesses")
    op.drop_table("businesses")
