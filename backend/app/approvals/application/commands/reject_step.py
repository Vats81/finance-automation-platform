import uuid
from dataclasses import dataclass

from app.approvals.application.ports import ApprovalsUnitOfWork
from app.approvals.domain.entities import ApprovalWorkflow
from app.approvals.domain.exceptions import ApprovalWorkflowNotFoundException
from app.identity.domain.value_objects import Role
from app.invoices.domain.exceptions import InvoiceNotFoundException


@dataclass(frozen=True)
class RejectStepCommand:
    workflow_id: uuid.UUID
    step_number: int
    approver_user_id: uuid.UUID
    actor_role: Role
    reason: str


class RejectStepUseCase:
    """A single rejection ends the whole workflow (no remaining steps run)
    and transitions the Invoice to REJECTED in the same transaction —
    see ApproveStepUseCase's docstring for why.
    """

    def __init__(self, uow: ApprovalsUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: RejectStepCommand) -> ApprovalWorkflow:
        workflow = await self._uow.approval_workflows.get_by_id(command.workflow_id)
        if workflow is None:
            raise ApprovalWorkflowNotFoundException(f"ApprovalWorkflow {command.workflow_id} not found")

        workflow.reject_step(
            step_number=command.step_number,
            approver_user_id=command.approver_user_id,
            actor_role=command.actor_role,
            reason=command.reason,
        )
        await self._uow.approval_workflows.update(workflow)

        invoice = await self._uow.invoices.get_by_id(workflow.invoice_id)
        if invoice is None:
            raise InvoiceNotFoundException(f"Invoice {workflow.invoice_id} not found")
        invoice.mark_rejected(command.reason)
        await self._uow.invoices.update(invoice)

        await self._uow.commit()
        return workflow
