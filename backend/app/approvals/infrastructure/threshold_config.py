from app.approvals.domain.value_objects import ApprovalThreshold
from app.config.settings import Settings


def load_approval_threshold(settings: Settings) -> ApprovalThreshold:
    """Reads APPROVAL_THRESHOLD_L1_MAX/L2_MAX (cents) from settings/.env.
    Static config for the foundation slice; Phase 2 makes this
    admin-configurable per PHASE2_ROADMAP.md rather than an env var.
    """
    return ApprovalThreshold(
        l1_max_cents=settings.approval_threshold_l1_max,
        l2_max_cents=settings.approval_threshold_l2_max,
    )
