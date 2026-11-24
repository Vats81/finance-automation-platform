"""how often a business wants its WhatsApp summary, and when one was last sent

Revision ID: 0036
Revises: 0035
Create Date: 2026-11-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0036"
down_revision: Union[str, None] = "0035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column("summary_frequency", sa.String(length=10), nullable=False, server_default="off"),
    )
    op.add_column("businesses", sa.Column("summary_last_sent_on", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("businesses", "summary_last_sent_on")
    op.drop_column("businesses", "summary_frequency")
