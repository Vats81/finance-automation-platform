"""create outbox_messages table

Revision ID: 0001
Revises:
Create Date: 2026-07-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "outbox_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_messages")),
        sa.UniqueConstraint("event_id", name=op.f("uq_outbox_messages_event_id")),
    )
    op.create_index(op.f("ix_outbox_messages_event_type"), "outbox_messages", ["event_type"])
    op.create_index(op.f("ix_outbox_messages_aggregate_id"), "outbox_messages", ["aggregate_id"])
    op.create_index(op.f("ix_outbox_messages_published_at"), "outbox_messages", ["published_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_outbox_messages_published_at"), table_name="outbox_messages")
    op.drop_index(op.f("ix_outbox_messages_aggregate_id"), table_name="outbox_messages")
    op.drop_index(op.f("ix_outbox_messages_event_type"), table_name="outbox_messages")
    op.drop_table("outbox_messages")
