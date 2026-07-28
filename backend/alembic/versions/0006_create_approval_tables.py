"""create approval_workflows and approval_steps tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "approval_workflows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_workflows")),
        sa.UniqueConstraint("invoice_id", name=op.f("uq_approval_workflows_invoice_id")),
    )
    op.create_index(op.f("ix_approval_workflows_invoice_id"), "approval_workflows", ["invoice_id"])

    op.create_table(
        "approval_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("required_role", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("approver_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comment", sa.String(length=1000), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_steps")),
        sa.ForeignKeyConstraint(
            ["workflow_id"],
            ["approval_workflows.id"],
            name=op.f("fk_approval_steps_workflow_id_approval_workflows"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(op.f("ix_approval_steps_workflow_id"), "approval_steps", ["workflow_id"])
    op.create_index(op.f("ix_approval_steps_status"), "approval_steps", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_approval_steps_status"), table_name="approval_steps")
    op.drop_index(op.f("ix_approval_steps_workflow_id"), table_name="approval_steps")
    op.drop_table("approval_steps")
    op.drop_index(op.f("ix_approval_workflows_invoice_id"), table_name="approval_workflows")
    op.drop_table("approval_workflows")
