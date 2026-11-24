"""the language of the messages Finverlo sends for a business (English or Hindi)

Revision ID: 0037
Revises: 0036
Create Date: 2026-11-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0037"
down_revision: Union[str, None] = "0036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("businesses", sa.Column("language", sa.String(length=5), nullable=False, server_default="en"))


def downgrade() -> None:
    op.drop_column("businesses", "language")
