from dataclasses import dataclass

from app.approvals.application.ports import ApprovalsUnitOfWork
from app.approvals.domain.entities import ApprovalWorkflow
from app.identity.domain.value_objects import Role
from app.shared.application.pagination import Page, PageRequest


@dataclass(frozen=True)
class ListPendingApprovalsForUserQuery:
    role: Role
    page: PageRequest


class ListPendingApprovalsForUserUseCase:
    """Pending, for a user, means pending for their role: RBAC is
    role-based, not per-user assignment, in this foundation slice, so any
    two users sharing a role see the same pending queue (whoever acts
    first claims the step; ApprovalWorkflow.approve_step's same-approver-
    can't-decide-twice guard is a different, workflow-scoped invariant).
    """

    def __init__(self, uow: ApprovalsUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListPendingApprovalsForUserQuery) -> Page[ApprovalWorkflow]:
        workflows, total = await self._uow.approval_workflows.list_pending_for_role(
            query.role, offset=query.page.offset, limit=query.page.limit
        )
        return Page(items=workflows, total=total, offset=query.page.offset, limit=query.page.limit)
