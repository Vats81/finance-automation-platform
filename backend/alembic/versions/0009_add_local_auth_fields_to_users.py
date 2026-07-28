"""add local auth fields to users

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # entra_object_id becomes optional: self-serve (LOCAL) auth users never
    # have one. Postgres unique constraints allow multiple NULLs, so
    # uq_users_entra_object_id still holds for ENTRA users.
    op.alter_column("users", "entra_object_id", existing_type=sa.String(length=255), nullable=True)

    op.add_column(
        "users",
        sa.Column("auth_provider", sa.String(length=20), nullable=False, server_default="entra"),
    )
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column(
        "users",
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("email_verification_token_hash", sa.String(length=64), nullable=True))
    op.add_column(
        "users", sa.Column("email_verification_expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("users", sa.Column("password_reset_token_hash", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("password_reset_expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_reset_expires_at")
    op.drop_column("users", "password_reset_token_hash")
    op.drop_column("users", "email_verification_expires_at")
    op.drop_column("users", "email_verification_token_hash")
    op.drop_column("users", "is_email_verified")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "auth_provider")
    op.alter_column("users", "entra_object_id", existing_type=sa.String(length=255), nullable=False)
