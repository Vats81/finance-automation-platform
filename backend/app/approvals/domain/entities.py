import uuid
from datetime import datetime, timezone

from app.approvals.domain.events import ApprovalWorkflowCompleted, StepApproved, StepRejected, WorkflowStarted
from app.approvals.domain.exceptions import (
    InvalidApprovalStepException,
    UnauthorizedApproverException,
    WorkflowAlreadyCompletedException,
)
from app.approvals.domain.value_objects import ApprovalStepStatus, ApprovalWorkflowStatus
from app.identity.domain.value_objects import Role
from app.shared.domain.aggregate_root import AggregateRoot
from app.shared.domain.base_entity import Entity


class ApprovalStep(Entity):
    """Child entity of ApprovalWorkflow — unlike PO/Invoice line items
    (value objects with no lifecycle), a step genuinely has one: it starts
    PENDING and is individually decided (who, when, what) independently of
    its siblings, which is what earns it entity status here.
    """

    def __init__(
        self,
        *,
        entity_id: uuid.UUID | None = None,
        step_number: int,
        required_role: Role,
        status: ApprovalStepStatus = ApprovalStepStatus.PENDING,
        approver_user_id: uuid.UUID | None = None,
        decided_at: datetime | None = None,
        comment: str | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.step_number = step_number
        self.required_role = required_role
        self.status = status
        self.approver_user_id = approver_user_id
        self.decided_at = decided_at
        self.comment = comment


class ApprovalWorkflow(AggregateRoot):
    """Own aggregate, deliberately separate from Invoice — embedding steps
    directly on Invoice would make every approver action lock/version the
    whole invoice row. Coordinated with Invoice purely via domain events
    routed through the outbox (WorkflowStarted reacts to InvoiceMatched;
    this aggregate's own completion, and Invoice's mark_approved/
    mark_rejected, are applied together in one DB transaction by
    approvals/application/commands/{approve_step,reject_step}.py — see
    those modules for why that one-transaction-two-aggregates choice is
    safe in a single-database monolith).
    """

    def __init__(
        self,
        *,
        entity_id: uuid.UUID | None = None,
        invoice_id: uuid.UUID,
        steps: list[ApprovalStep],
        status: ApprovalWorkflowStatus = ApprovalWorkflowStatus.IN_PROGRESS,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.invoice_id = invoice_id
        self.steps = sorted(steps, key=lambda s: s.step_number)
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)

    @classmethod
    def start(cls, *, invoice_id: uuid.UUID, required_roles: list[Role]) -> "ApprovalWorkflow":
        steps = [
            ApprovalStep(step_number=i + 1, required_role=role) for i, role in enumerate(required_roles)
        ]
        workflow = cls(invoice_id=invoice_id, steps=steps)
        workflow._record_event(
            WorkflowStarted(aggregate_id=workflow.id, invoice_id=str(invoice_id), step_count=len(steps))
        )
        return workflow

    @property
    def current_step(self) -> ApprovalStep | None:
        """The next step awaiting a decision, or None if the workflow is
        complete. Public — used both to guard approve/reject calls and by
        the repository's list_pending_for_role query and API responses.
        """
        return next((s for s in self.steps if s.status == ApprovalStepStatus.PENDING), None)

    def _guard_can_decide(
        self, step_number: int, approver_user_id: uuid.UUID, actor_role: Role
    ) -> ApprovalStep:
        if self.status != ApprovalWorkflowStatus.IN_PROGRESS:
            raise WorkflowAlreadyCompletedException(f"Workflow {self.id} is already {self.status.value}")

        current = self.current_step
        if current is None or current.step_number != step_number:
            raise InvalidApprovalStepException(
                f"Step {step_number} is not the current pending step for workflow {self.id}"
            )
        if current.required_role != actor_role:
            raise UnauthorizedApproverException(
                f"Step {step_number} requires role {current.required_role.value}, "
                f"actor has {actor_role.value}"
            )
        already_decided = any(
            s.approver_user_id == approver_user_id and s.status != ApprovalStepStatus.PENDING
            for s in self.steps
        )
        if already_decided:
            raise UnauthorizedApproverException(
                f"User {approver_user_id} has already decided a step in workflow {self.id}"
            )
        return current

    def approve_step(self, *, step_number: int, approver_user_id: uuid.UUID, actor_role: Role) -> None:
        step = self._guard_can_decide(step_number, approver_user_id, actor_role)

        step.status = ApprovalStepStatus.APPROVED
        step.approver_user_id = approver_user_id
        step.decided_at = datetime.now(timezone.utc)
        self._record_event(
            StepApproved(
                aggregate_id=self.id,
                invoice_id=str(self.invoice_id),
                step_number=step_number,
                approver_user_id=str(approver_user_id),
            )
        )

        if self.current_step is None:
            self.status = ApprovalWorkflowStatus.APPROVED
            self._record_event(
                ApprovalWorkflowCompleted(
                    aggregate_id=self.id, invoice_id=str(self.invoice_id), outcome="approved"
                )
            )

    def reject_step(
        self, *, step_number: int, approver_user_id: uuid.UUID, actor_role: Role, reason: str
    ) -> None:
        step = self._guard_can_decide(step_number, approver_user_id, actor_role)

        step.status = ApprovalStepStatus.REJECTED
        step.approver_user_id = approver_user_id
        step.decided_at = datetime.now(timezone.utc)
        step.comment = reason
        self._record_event(
            StepRejected(
                aggregate_id=self.id,
                invoice_id=str(self.invoice_id),
                step_number=step_number,
                approver_user_id=str(approver_user_id),
                reason=reason,
            )
        )

        self.status = ApprovalWorkflowStatus.REJECTED
        self._record_event(
            ApprovalWorkflowCompleted(
                aggregate_id=self.id, invoice_id=str(self.invoice_id), outcome="rejected"
            )
        )

    @property
    def is_completed(self) -> bool:
        return self.status != ApprovalWorkflowStatus.IN_PROGRESS
