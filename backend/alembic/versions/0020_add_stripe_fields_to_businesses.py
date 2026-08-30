"""add stripe fields to businesses

Revision ID: 0020
Revises: 0019
Create Date: 2026-08-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("businesses", sa.Column("stripe_customer_id", sa.String(length=255), nullable=True))
    op.add_column("businesses", sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True))
    op.create_index(
        "ix_businesses_stripe_subscription_id", "businesses", ["stripe_subscription_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_businesses_stripe_subscription_id", table_name="businesses")
    op.drop_column("businesses", "stripe_subscription_id")
    op.drop_column("businesses", "stripe_customer_id")
