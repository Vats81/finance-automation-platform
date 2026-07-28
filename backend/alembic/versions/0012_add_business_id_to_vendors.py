"""add business_id to vendors

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable: AP-automation vendors (created before/without a business
    # context) keep business_id = NULL and are unaffected. Only vendors
    # created through the SMB product's /businesses/{business_id}/vendors
    # routes set this.
    op.add_column("vendors", sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_vendors_business_id"), "vendors", ["business_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_vendors_business_id"), table_name="vendors")
    op.drop_column("vendors", "business_id")
