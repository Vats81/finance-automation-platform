import uuid
from dataclasses import dataclass

from app.approvals.application.ports import ApprovalsUnitOfWork
from app.approvals.domain.entities import ApprovalWorkflow
from app.approvals.domain.exceptions import ApprovalWorkflowNotFoundException
from app.identity.domain.value_objects import Role
from app.invoices.domain.exceptions import InvoiceNotFoundException


@dataclass(frozen=True)
class ApproveStepCommand:
    workflow_id: uuid.UUID
    step_number: int
    approver_user_id: uuid.UUID
    actor_role: Role


class ApproveStepUseCase:
    """If this approval completes the workflow, also transitions the
    Invoice to APPROVED in the same transaction — see
    start_approval_workflow.py's docstring for why that's safe here.
    Invoice.mark_approved() raises InvoiceApproved, which is what
    payments/application/event_handlers.py reacts to (task 11) to
    schedule payment; this use case does not know about payments at all.
    """

    def __init__(self, uow: ApprovalsUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: ApproveStepCommand) -> ApprovalWorkflow:
        workflow = await self._uow.approval_workflows.get_by_id(command.workflow_id)
        if workflow is None:
            raise ApprovalWorkflowNotFoundException(f"ApprovalWorkflow {command.workflow_id} not found")

        workflow.approve_step(
            step_number=command.step_number,
            approver_user_id=command.approver_user_id,
            actor_role=command.actor_role,
        )
        await self._uow.approval_workflows.update(workflow)

        if workflow.is_completed:
            invoice = await self._uow.invoices.get_by_id(workflow.invoice_id)
            if invoice is None:
                raise InvoiceNotFoundException(f"Invoice {workflow.invoice_id} not found")
            invoice.mark_approved()
            await self._uow.invoices.update(invoice)

        await self._uow.commit()
        return workflow
