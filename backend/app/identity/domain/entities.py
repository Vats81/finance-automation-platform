import hashlib
import uuid
from datetime import datetime, timezone

from app.identity.domain.events import (
    EmailVerified,
    PasswordResetRequested,
    PasswordWasReset,
    UserDeactivated,
    UserProvisioned,
    UserRegistered,
    UserRoleChanged,
)
from app.identity.domain.exceptions import InvalidOrExpiredTokenException, UserDeactivatedException
from app.identity.domain.value_objects import AuthProvider, EmailAddress, Role
from app.shared.domain.aggregate_root import AggregateRoot


def _hash_token(token: str) -> str:
    """One-time link tokens (email verification, password reset) are
    generated with `secrets.token_urlsafe` at the application layer (already
    high-entropy), so a fast deterministic hash is appropriate here — unlike
    passwords, which go through the deliberately-slow IPasswordHasher port.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class User(AggregateRoot):
    """A platform user. Two provisioning paths share this aggregate:

    - ENTRA: JIT-provisioned from Entra ID claims on first login (the
      AP-automation product) via `provision()` — unchanged behavior.
    - LOCAL: self-serve email+password signup (the SMB Finance Manager
      product) via `register()`, gated by email verification before login
      is allowed (see identity/application/commands/login_user.py).

    `role` (the coarse AP_CLERK/APPROVER/FINANCE_ADMIN enum) is vestigial for
    LOCAL users — it defaults to AP_CLERK as a neutral placeholder rather
    than restructuring every existing AP-automation consumer of this column.
    Business-level authorization for LOCAL users lives in
    business.domain.entities.BusinessMembership.role instead.
    """

    def __init__(
        self,
        *,
        entity_id: uuid.UUID | None = None,
        entra_object_id: str | None = None,
        email: EmailAddress,
        display_name: str,
        role: Role,
        auth_provider: AuthProvider = AuthProvider.ENTRA,
        password_hash: str | None = None,
        is_email_verified: bool = False,
        email_verification_token_hash: str | None = None,
        email_verification_expires_at: datetime | None = None,
        password_reset_token_hash: str | None = None,
        password_reset_expires_at: datetime | None = None,
        is_active: bool = True,
        is_platform_admin: bool = False,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.entra_object_id = entra_object_id
        self.email = email
        self.display_name = display_name
        self.role = role
        self.auth_provider = auth_provider
        self.password_hash = password_hash
        self.is_email_verified = is_email_verified
        self.email_verification_token_hash = email_verification_token_hash
        self.email_verification_expires_at = email_verification_expires_at
        self.password_reset_token_hash = password_reset_token_hash
        self.password_reset_expires_at = password_reset_expires_at
        self.is_active = is_active
        self.is_platform_admin = is_platform_admin
        self.created_at = created_at or datetime.now(timezone.utc)

    @classmethod
    def provision(cls, *, entra_object_id: str, email: EmailAddress, display_name: str) -> "User":
        """First-seen login: default to the least-privileged role. An
        existing FINANCE_ADMIN promotes new hires via the /users endpoint.
        """
        user = cls(
            entra_object_id=entra_object_id,
            email=email,
            display_name=display_name,
            role=Role.AP_CLERK,
            auth_provider=AuthProvider.ENTRA,
            is_email_verified=True,
        )
        user._record_event(
            UserProvisioned(
                aggregate_id=user.id,
                entra_object_id=entra_object_id,
                email=str(email),
                role=user.role.value,
            )
        )
        return user

    @classmethod
    def register(
        cls,
        *,
        email: EmailAddress,
        display_name: str,
        password_hash: str,
        verification_token: str,
        verification_expires_at: datetime,
    ) -> "User":
        """Self-serve signup for the SMB Finance Manager product. Email is
        unverified until `verify_email()` succeeds; login is refused until
        then (see LoginUserUseCase).
        """
        user = cls(
            email=email,
            display_name=display_name,
            role=Role.AP_CLERK,
            auth_provider=AuthProvider.LOCAL,
            password_hash=password_hash,
            is_email_verified=False,
            email_verification_token_hash=_hash_token(verification_token),
            email_verification_expires_at=verification_expires_at,
        )
        user._record_event(
            UserRegistered(
                aggregate_id=user.id,
                email=str(email),
                display_name=display_name,
                verification_token=verification_token,
                verification_expires_at=verification_expires_at,
            )
        )
        return user

    def verify_email(self, *, token: str, now: datetime) -> None:
        if self.is_email_verified:
            return
        if self.email_verification_token_hash is None or self.email_verification_expires_at is None:
            raise InvalidOrExpiredTokenException("No email verification is pending for this user")
        if now > self.email_verification_expires_at:
            raise InvalidOrExpiredTokenException("Email verification link has expired")
        if _hash_token(token) != self.email_verification_token_hash:
            raise InvalidOrExpiredTokenException("Invalid email verification token")

        self.is_email_verified = True
        self.email_verification_token_hash = None
        self.email_verification_expires_at = None
        self._record_event(EmailVerified(aggregate_id=self.id, email=str(self.email)))

    def request_password_reset(self, *, reset_token: str, expires_at: datetime) -> None:
        self.password_reset_token_hash = _hash_token(reset_token)
        self.password_reset_expires_at = expires_at
        self._record_event(
            PasswordResetRequested(
                aggregate_id=self.id,
                email=str(self.email),
                reset_token=reset_token,
                reset_expires_at=expires_at,
            )
        )

    def reset_password(self, *, token: str, new_password_hash: str, now: datetime) -> None:
        if self.password_reset_token_hash is None or self.password_reset_expires_at is None:
            raise InvalidOrExpiredTokenException("No password reset is pending for this user")
        if now > self.password_reset_expires_at:
            raise InvalidOrExpiredTokenException("Password reset link has expired")
        if _hash_token(token) != self.password_reset_token_hash:
            raise InvalidOrExpiredTokenException("Invalid password reset token")

        self.password_hash = new_password_hash
        self.password_reset_token_hash = None
        self.password_reset_expires_at = None
        self._record_event(PasswordWasReset(aggregate_id=self.id, email=str(self.email)))

    def change_role(self, *, new_role: Role, changed_by_user_id: uuid.UUID) -> None:
        if not self.is_active:
            raise UserDeactivatedException(f"User {self.id} is deactivated and cannot be modified")
        if new_role == self.role:
            return
        previous_role = self.role
        self.role = new_role
        self._record_event(
            UserRoleChanged(
                aggregate_id=self.id,
                previous_role=previous_role.value,
                new_role=new_role.value,
                changed_by_user_id=str(changed_by_user_id),
            )
        )

    def deactivate(self) -> None:
        """Same simple-toggle precedent as Product.deactivate()/reactivate()
        (inventory/domain/entities.py) — records an event on the "negative"
        transition, none on the way back, no guard against a redundant
        call. Previously recorded no event at all; adding one now since an
        admin deactivating an account is exactly the kind of action that
        should leave an audit trail.
        """
        self.is_active = False
        self._record_event(UserDeactivated(aggregate_id=self.id, email=str(self.email)))

    def reactivate(self) -> None:
        self.is_active = True

    def has_role(self, *roles: Role) -> bool:
        return self.is_active and self.role in roles
