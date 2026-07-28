import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.approvals.domain.entities import ApprovalWorkflow
from app.approvals.domain.exceptions import ApprovalWorkflowNotFoundException
from app.approvals.domain.repository import IApprovalWorkflowRepository
from app.approvals.domain.value_objects import ApprovalWorkflowStatus
from app.approvals.infrastructure.mappers import (
    apply_domain_to_existing_model,
    domain_to_model,
    model_to_domain,
)
from app.approvals.infrastructure.models import ApprovalWorkflowModel
from app.identity.domain.value_objects import Role
from app.shared.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemyApprovalWorkflowRepository(IApprovalWorkflowRepository):
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> AsyncSession:
        return self._uow.session

    async def get_by_id(self, workflow_id: uuid.UUID) -> ApprovalWorkflow | None:
        stmt = (
            select(ApprovalWorkflowModel)
            .options(selectinload(ApprovalWorkflowModel.steps))
            .where(ApprovalWorkflowModel.id == workflow_id)
        )
        result = await self._session.execute(stmt)
        model = result.unique().scalar_one_or_none()
        return model_to_domain(model) if model else None

    async def get_by_invoice_id(self, invoice_id: uuid.UUID) -> ApprovalWorkflow | None:
        stmt = (
            select(ApprovalWorkflowModel)
            .options(selectinload(ApprovalWorkflowModel.steps))
            .where(ApprovalWorkflowModel.invoice_id == invoice_id)
        )
        result = await self._session.execute(stmt)
        model = result.unique().scalar_one_or_none()
        return model_to_domain(model) if model else None

    async def list_pending_for_role(
        self, role: Role, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[ApprovalWorkflow], int]:
        # The "current" step is a property of ordered step state, not a
        # column, so filtering by "is this workflow actionable by `role`
        # right now" happens in Python after loading in-progress workflows
        # rather than in SQL. Fine at foundation-slice scale; worth an
        # index-backed materialized "current_step_role" column if this
        # becomes a hot path later.
        stmt = (
            select(ApprovalWorkflowModel)
            .options(selectinload(ApprovalWorkflowModel.steps))
            .where(ApprovalWorkflowModel.status == ApprovalWorkflowStatus.IN_PROGRESS.value)
            .order_by(ApprovalWorkflowModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        workflows = [model_to_domain(m) for m in result.unique().scalars().all()]
        matching = [
            wf for wf in workflows if wf.current_step is not None and wf.current_step.required_role == role
        ]
        return matching[offset : offset + limit], len(matching)

    def add(self, workflow: ApprovalWorkflow) -> None:
        self._session.add(domain_to_model(workflow))
        self._uow.collect_events(workflow)

    async def update(self, workflow: ApprovalWorkflow) -> None:
        stmt = (
            select(ApprovalWorkflowModel)
            .options(selectinload(ApprovalWorkflowModel.steps))
            .where(ApprovalWorkflowModel.id == workflow.id)
        )
        result = await self._session.execute(stmt)
        model = result.unique().scalar_one_or_none()
        if model is None:
            raise ApprovalWorkflowNotFoundException(f"ApprovalWorkflow {workflow.id} not found")
        apply_domain_to_existing_model(workflow, model)
        self._uow.collect_events(workflow)
