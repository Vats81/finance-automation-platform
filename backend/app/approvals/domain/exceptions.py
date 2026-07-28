from app.shared.domain.exceptions import (
    ConflictException,
    NotFoundException,
    UnauthorizedDomainActionException,
)


class ApprovalWorkflowNotFoundException(NotFoundException):
    error_code = "approval_workflow_not_found"


class WorkflowAlreadyCompletedException(ConflictException):
    error_code = "workflow_already_completed"


class InvalidApprovalStepException(ConflictException):
    """Raised when a step is acted on out of sequence or after it has
    already been decided.
    """

    error_code = "invalid_approval_step"


class UnauthorizedApproverException(UnauthorizedDomainActionException):
    """Domain-level defense-in-depth: the acting user's role doesn't match
    what this specific step requires, or they already approved an earlier
    step in the same workflow (no self-multi-approval).
    """

    error_code = "unauthorized_approver"
