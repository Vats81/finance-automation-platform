"""when a beta invitation email was sent to a waitlist entry

Revision ID: 0031
Revises: 0030
Create Date: 2026-11-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0031"
down_revision: Union[str, None] = "0030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "beta_waitlist_entries", sa.Column("invitation_sent_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("beta_waitlist_entries", "invitation_sent_at")
