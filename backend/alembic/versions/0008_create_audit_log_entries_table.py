"""create audit_log_entries table

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_log_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log_entries")),
    )
    op.create_index(op.f("ix_audit_log_entries_event_type"), "audit_log_entries", ["event_type"])
    op.create_index(op.f("ix_audit_log_entries_aggregate_id"), "audit_log_entries", ["aggregate_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_log_entries_aggregate_id"), table_name="audit_log_entries")
    op.drop_index(op.f("ix_audit_log_entries_event_type"), table_name="audit_log_entries")
    op.drop_table("audit_log_entries")
