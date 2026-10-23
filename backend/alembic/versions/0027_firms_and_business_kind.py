"""accounting firms, and a kind (business / personal) on workspaces

Revision ID: 0027
Revises: 0026
Create Date: 2026-10-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027"
down_revision: Union[str, None] = "0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "firms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_firms")),
    )
    op.create_index(op.f("ix_firms_owner_user_id"), "firms", ["owner_user_id"])

    op.create_table(
        "firm_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_firm_memberships")),
        sa.UniqueConstraint("firm_id", "user_id", name="uq_firm_memberships_firm_user"),
    )
    op.create_index(op.f("ix_firm_memberships_firm_id"), "firm_memberships", ["firm_id"])
    op.create_index(op.f("ix_firm_memberships_user_id"), "firm_memberships", ["user_id"])

    op.add_column("businesses", sa.Column("kind", sa.String(length=20), nullable=False, server_default="business"))
    op.add_column("businesses", sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_businesses_firm_id"), "businesses", ["firm_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_businesses_firm_id"), table_name="businesses")
    op.drop_column("businesses", "firm_id")
    op.drop_column("businesses", "kind")
    op.drop_index(op.f("ix_firm_memberships_user_id"), table_name="firm_memberships")
    op.drop_index(op.f("ix_firm_memberships_firm_id"), table_name="firm_memberships")
    op.drop_table("firm_memberships")
    op.drop_index(op.f("ix_firms_owner_user_id"), table_name="firms")
    op.drop_table("firms")
