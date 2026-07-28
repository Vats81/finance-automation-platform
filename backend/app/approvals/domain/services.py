from app.approvals.domain.value_objects import ApprovalThreshold
from app.identity.domain.value_objects import Role
from app.shared.domain.value_objects import Money


class ApprovalChainBuilder:
    """Threshold-based approval chain: escalates both the number of steps
    and who must sign off as the invoice amount increases. Pure domain
    logic — takes a Money amount and a threshold configuration, returns the
    role sequence for ApprovalWorkflow.start() to turn into steps.
    """

    def __init__(self, threshold: ApprovalThreshold) -> None:
        self._threshold = threshold

    def build_chain(self, total_amount: Money) -> list[Role]:
        cents = total_amount.cents
        if cents <= self._threshold.l1_max_cents:
            return [Role.APPROVER]
        if cents <= self._threshold.l2_max_cents:
            return [Role.APPROVER, Role.FINANCE_ADMIN]
        # Above the higher threshold: extra scrutiny — a second, independent
        # Finance Admin sign-off (ApprovalWorkflow forbids the same user
        # deciding two steps, so this genuinely requires two different people).
        return [Role.APPROVER, Role.FINANCE_ADMIN, Role.FINANCE_ADMIN]
