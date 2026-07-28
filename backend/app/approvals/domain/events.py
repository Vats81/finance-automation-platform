from dataclasses import dataclass

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class WorkflowStarted(DomainEvent):
    invoice_id: str
    step_count: int


@dataclass(frozen=True, kw_only=True)
class StepApproved(DomainEvent):
    invoice_id: str
    step_number: int
    approver_user_id: str


@dataclass(frozen=True, kw_only=True)
class StepRejected(DomainEvent):
    invoice_id: str
    step_number: int
    approver_user_id: str
    reason: str


@dataclass(frozen=True, kw_only=True)
class ApprovalWorkflowCompleted(DomainEvent):
    invoice_id: str
    outcome: str
