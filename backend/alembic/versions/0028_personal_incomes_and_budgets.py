"""income records and category budgets for personal workspaces

Revision ID: 0028
Revises: 0027
Create Date: 2026-10-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028"
down_revision: Union[str, None] = "0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "incomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("income_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="recorded"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incomes")),
    )
    op.create_index(op.f("ix_incomes_business_id"), "incomes", ["business_id"])

    op.create_table(
        "budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("category_key", sa.String(length=100), nullable=False),
        sa.Column("monthly_limit_cents", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_budgets")),
        sa.UniqueConstraint("business_id", "category_key", name="uq_budgets_business_category"),
    )
    op.create_index(op.f("ix_budgets_business_id"), "budgets", ["business_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_budgets_business_id"), table_name="budgets")
    op.drop_table("budgets")
    op.drop_index(op.f("ix_incomes_business_id"), table_name="incomes")
    op.drop_table("incomes")
