"""create business_memberships table

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "business_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_business_memberships")),
    )
    op.create_index(op.f("ix_business_memberships_business_id"), "business_memberships", ["business_id"])
    op.create_index(op.f("ix_business_memberships_user_id"), "business_memberships", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_business_memberships_user_id"), table_name="business_memberships")
    op.drop_index(op.f("ix_business_memberships_business_id"), table_name="business_memberships")
    op.drop_table("business_memberships")
