"""billing plan and Stripe references on firms

Revision ID: 0030
Revises: 0029
Create Date: 2026-11-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0030"
down_revision: Union[str, None] = "0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("firms", sa.Column("plan", sa.String(length=20), nullable=False, server_default="free"))
    op.add_column("firms", sa.Column("stripe_customer_id", sa.String(length=255), nullable=True))
    op.add_column("firms", sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_firms_stripe_subscription_id"), "firms", ["stripe_subscription_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_firms_stripe_subscription_id"), table_name="firms")
    op.drop_column("firms", "stripe_subscription_id")
    op.drop_column("firms", "stripe_customer_id")
    op.drop_column("firms", "plan")
