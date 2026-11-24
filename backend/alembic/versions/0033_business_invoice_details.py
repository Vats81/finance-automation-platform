"""the seller details a GST invoice prints: GSTIN, address, state, PIN, phone, UPI ID

Revision ID: 0033
Revises: 0032
Create Date: 2026-11-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0033"
down_revision: Union[str, None] = "0032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("businesses", sa.Column("gstin", sa.String(length=15), nullable=True))
    op.add_column("businesses", sa.Column("address_line", sa.String(length=255), nullable=True))
    op.add_column("businesses", sa.Column("city", sa.String(length=120), nullable=True))
    op.add_column("businesses", sa.Column("state_code", sa.String(length=2), nullable=True))
    op.add_column("businesses", sa.Column("pincode", sa.String(length=6), nullable=True))
    op.add_column("businesses", sa.Column("phone", sa.String(length=32), nullable=True))
    op.add_column("businesses", sa.Column("upi_id", sa.String(length=100), nullable=True))


def downgrade() -> None:
    for column in ("upi_id", "phone", "pincode", "state_code", "city", "address_line", "gstin"):
        op.drop_column("businesses", column)
