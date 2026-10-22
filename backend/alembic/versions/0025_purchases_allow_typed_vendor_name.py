"""let a purchase name its supplier by typed text instead of a saved vendor

Revision ID: 0025
Revises: 0024
Create Date: 2026-10-22

Downgrade note: restoring NOT NULL on vendor_id fails if any purchase was
recorded with only a vendor name; those rows must be given a vendor first.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025"
down_revision: Union[str, None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("purchases", sa.Column("vendor_name", sa.String(length=200), nullable=True))
    op.alter_column("purchases", "vendor_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)


def downgrade() -> None:
    op.alter_column("purchases", "vendor_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.drop_column("purchases", "vendor_name")
