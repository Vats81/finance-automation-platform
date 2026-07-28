from typing import Protocol

from app.approvals.domain.repository import IApprovalWorkflowRepository
from app.invoices.domain.repository import IInvoiceRepository


class ApprovalsUnitOfWork(Protocol):
    """See identity/application/ports.py for why this Protocol exists and
    why repos are declared as `@property` rather than plain attributes.
    Includes `invoices` alongside `approval_workflows` because
    StartApprovalWorkflowUseCase/ApproveStepUseCase/RejectStepUseCase all
    transition the Invoice in the same transaction as the workflow change
    (see those modules' docstrings for why that's safe here).
    """

    @property
    def approval_workflows(self) -> IApprovalWorkflowRepository: ...

    @property
    def invoices(self) -> IInvoiceRepository: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
