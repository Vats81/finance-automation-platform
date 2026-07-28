import enum
from dataclasses import dataclass

from app.shared.domain.base_value_object import ValueObject
from app.shared.domain.exceptions import ValidationException


class ApprovalStepStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalWorkflowStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ApprovalThreshold(ValueObject):
    """Amount boundary (in cents, USD) that determines how many approval
    steps — and which roles — a workflow requires. See
    approvals/domain/services.py:ApprovalChainBuilder for how thresholds
    become a concrete step chain, and approvals/infrastructure/threshold_config.py
    for where the configured values come from.
    """

    l1_max_cents: int
    l2_max_cents: int

    def __post_init__(self) -> None:
        if self.l1_max_cents <= 0 or self.l2_max_cents <= self.l1_max_cents:
            raise ValidationException("Approval thresholds must be positive and strictly increasing")
