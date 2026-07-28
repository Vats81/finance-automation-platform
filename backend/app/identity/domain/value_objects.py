import enum
import re
from dataclasses import dataclass

from app.shared.domain.base_value_object import ValueObject
from app.shared.domain.exceptions import ValidationException

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Role(str, enum.Enum):
    """Coarse RBAC roles for the foundation slice.

    Sourced from the local User table (assigned via the /users admin
    endpoint) rather than synced from Entra App Roles, to avoid requiring
    tenant-admin consent during local development. Syncing from Entra App
    Roles is a Phase 2 item (see PHASE2_ROADMAP.md).
    """

    AP_CLERK = "ap_clerk"
    APPROVER = "approver"
    FINANCE_ADMIN = "finance_admin"


class AuthProvider(str, enum.Enum):
    """Distinguishes JIT-provisioned Entra ID users (the AP-automation
    product) from self-serve email+password users (the SMB Finance Manager
    product) sharing the same `users` table. Business-level authorization
    for LOCAL users lives in business.domain.entities.BusinessMembership.role,
    not on this row — see business/ bounded context.
    """

    ENTRA = "entra"
    LOCAL = "local"


@dataclass(frozen=True)
class EmailAddress(ValueObject):
    value: str

    def __post_init__(self) -> None:
        if not _EMAIL_RE.match(self.value):
            raise ValidationException(f"'{self.value}' is not a valid email address")

    def __str__(self) -> str:
        return self.value
