import uuid
from dataclasses import dataclass

from app.approvals.application.ports import ApprovalsUnitOfWork
from app.approvals.domain.entities import ApprovalWorkflow
from app.approvals.domain.services import ApprovalChainBuilder
from app.approvals.domain.value_objects import ApprovalThreshold
from app.invoices.domain.exceptions import InvoiceNotFoundException


@dataclass(frozen=True)
class StartApprovalWorkflowCommand:
    invoice_id: uuid.UUID


class StartApprovalWorkflowUseCase:
    """Reacts to InvoiceMatched (see approvals/application/event_handlers.py).
    Builds the threshold-based chain, persists the new ApprovalWorkflow,
    and transitions the Invoice to PENDING_APPROVAL — both in one DB
    transaction. That crosses an aggregate boundary in a single commit,
    which the platform otherwise avoids (see shared kernel docs), but it's
    deliberate here: this whole use case IS the single reaction to one
    event, both aggregates live in the same database, and one atomic
    commit is strictly safer than splitting it into a second outbox hop
    that could leave the invoice stuck in MATCHED if the process died
    in between.
    """

    def __init__(self, uow: ApprovalsUnitOfWork, threshold: ApprovalThreshold) -> None:
        self._uow = uow
        self._chain_builder = ApprovalChainBuilder(threshold)

    async def execute(self, command: StartApprovalWorkflowCommand) -> ApprovalWorkflow:
        invoice = await self._uow.invoices.get_by_id(command.invoice_id)
        if invoice is None:
            raise InvoiceNotFoundException(f"Invoice {command.invoice_id} not found")

        required_roles = self._chain_builder.build_chain(invoice.total_amount)
        workflow = ApprovalWorkflow.start(invoice_id=invoice.id, required_roles=required_roles)
        self._uow.approval_workflows.add(workflow)

        invoice.mark_pending_approval()
        await self._uow.invoices.update(invoice)

        await self._uow.commit()
        return workflow
