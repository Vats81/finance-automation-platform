from dataclasses import dataclass
from datetime import datetime

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class UserProvisioned(DomainEvent):
    entra_object_id: str
    email: str
    role: str


@dataclass(frozen=True, kw_only=True)
class UserRoleChanged(DomainEvent):
    previous_role: str
    new_role: str
    changed_by_user_id: str


@dataclass(frozen=True, kw_only=True)
class UserRegistered(DomainEvent):
    """Carries the plaintext verification token so the async notification
    handler (bootstrap/event_handlers.py -> workers/tasks/notification_tasks.py)
    can build the verification link without re-deriving or storing the
    secret anywhere else. Same event-driven, outbox-relayed pattern already
    used for InvoiceSubmitted -> OCR enqueue (invoices/application/event_handlers.py).
    """

    email: str
    display_name: str
    verification_token: str
    verification_expires_at: datetime


@dataclass(frozen=True, kw_only=True)
class EmailVerified(DomainEvent):
    email: str


@dataclass(frozen=True, kw_only=True)
class PasswordResetRequested(DomainEvent):
    email: str
    reset_token: str
    reset_expires_at: datetime


@dataclass(frozen=True, kw_only=True)
class PasswordWasReset(DomainEvent):
    email: str


@dataclass(frozen=True, kw_only=True)
class UserDeactivated(DomainEvent):
    email: str
