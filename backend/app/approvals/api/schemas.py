import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.approvals.domain.entities import ApprovalWorkflow
from app.approvals.domain.value_objects import ApprovalStepStatus, ApprovalWorkflowStatus
from app.identity.domain.value_objects import Role


class ApprovalStepResponse(BaseModel):
    step_number: int
    required_role: Role
    status: ApprovalStepStatus
    approver_user_id: uuid.UUID | None
    decided_at: datetime | None
    comment: str | None


class ApprovalWorkflowResponse(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    status: ApprovalWorkflowStatus
    steps: list[ApprovalStepResponse]
    created_at: datetime

    @classmethod
    def from_domain(cls, workflow: ApprovalWorkflow) -> "ApprovalWorkflowResponse":
        return cls(
            id=workflow.id,
            invoice_id=workflow.invoice_id,
            status=workflow.status,
            steps=[
                ApprovalStepResponse(
                    step_number=s.step_number,
                    required_role=s.required_role,
                    status=s.status,
                    approver_user_id=s.approver_user_id,
                    decided_at=s.decided_at,
                    comment=s.comment,
                )
                for s in workflow.steps
            ],
            created_at=workflow.created_at,
        )


class PagedApprovalWorkflowsResponse(BaseModel):
    items: list[ApprovalWorkflowResponse]
    total: int
    offset: int
    limit: int


class RejectStepRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)
