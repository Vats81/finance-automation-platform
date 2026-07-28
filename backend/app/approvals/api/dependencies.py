from app.identity.api.dependencies import require_role
from app.identity.domain.value_objects import Role

# Any elevated role may attempt to act on a step; ApprovalWorkflow itself
# enforces that the acting user's role matches what the specific step
# requires (see approvals/domain/entities.py:_guard_can_decide).
require_approver = require_role(Role.APPROVER, Role.FINANCE_ADMIN)
