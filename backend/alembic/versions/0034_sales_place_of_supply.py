"""the state a sale is supplied to (GST place of supply)

Revision ID: 0034
Revises: 0033
Create Date: 2026-11-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0034"
down_revision: Union[str, None] = "0033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sales", sa.Column("place_of_supply", sa.String(length=2), nullable=True))


def downgrade() -> None:
    op.drop_column("sales", "place_of_supply")
