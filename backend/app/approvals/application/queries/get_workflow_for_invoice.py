import uuid
from dataclasses import dataclass

from app.approvals.application.ports import ApprovalsUnitOfWork
from app.approvals.domain.entities import ApprovalWorkflow
from app.approvals.domain.exceptions import ApprovalWorkflowNotFoundException


@dataclass(frozen=True)
class GetWorkflowForInvoiceQuery:
    invoice_id: uuid.UUID


class GetWorkflowForInvoiceUseCase:
    def __init__(self, uow: ApprovalsUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: GetWorkflowForInvoiceQuery) -> ApprovalWorkflow:
        workflow = await self._uow.approval_workflows.get_by_invoice_id(query.invoice_id)
        if workflow is None:
            raise ApprovalWorkflowNotFoundException(f"No approval workflow for invoice {query.invoice_id}")
        return workflow
