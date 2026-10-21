"""create beta_waitlist_entries table

Revision ID: 0024
Revises: 0023
Create Date: 2026-10-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "beta_waitlist_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("work_email", sa.String(length=320), nullable=False),
        sa.Column("business_name", sa.String(length=200), nullable=True),
        sa.Column("business_type", sa.String(length=100), nullable=True),
        sa.Column("bookkeeping_method", sa.String(length=100), nullable=True),
        sa.Column("reporting_problem", sa.String(length=1000), nullable=True),
        sa.Column("weekly_feedback_ok", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="interested"),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_beta_waitlist_entries")),
        sa.UniqueConstraint("work_email", name=op.f("uq_beta_waitlist_entries_work_email")),
    )
    op.create_index(op.f("ix_beta_waitlist_entries_status"), "beta_waitlist_entries", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_beta_waitlist_entries_status"), table_name="beta_waitlist_entries")
    op.drop_table("beta_waitlist_entries")
