import uuid
from abc import ABC, abstractmethod

from app.approvals.domain.entities import ApprovalWorkflow
from app.identity.domain.value_objects import Role


class IApprovalWorkflowRepository(ABC):
    @abstractmethod
    async def get_by_id(self, workflow_id: uuid.UUID) -> ApprovalWorkflow | None: ...

    @abstractmethod
    async def get_by_invoice_id(self, invoice_id: uuid.UUID) -> ApprovalWorkflow | None: ...

    @abstractmethod
    async def list_pending_for_role(
        self, role: Role, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[ApprovalWorkflow], int]: ...

    @abstractmethod
    def add(self, workflow: ApprovalWorkflow) -> None: ...

    @abstractmethod
    async def update(self, workflow: ApprovalWorkflow) -> None: ...
