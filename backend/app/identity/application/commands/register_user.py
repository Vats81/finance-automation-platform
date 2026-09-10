import secrets
from dataclasses import dataclass
from datetime import timedelta

from app.identity.application.ports import IdentityUnitOfWork
from app.identity.domain.entities import User
from app.identity.domain.exceptions import EmailAlreadyRegisteredException
from app.identity.domain.value_objects import EmailAddress
from app.shared.application.ports import IClock, IPasswordHasher


@dataclass(frozen=True)
class RegisterUserCommand:
    email: str
    password: str
    display_name: str


class RegisterUserUseCase:
    """Self-serve signup for the SMB Finance Manager product. Distinct from
    ProvisionUserUseCase (Entra JIT provisioning, idempotent-by-design) —
    this is an explicitly-invoked command that must reject duplicate emails
    and never silently no-ops.
    """

    def __init__(
        self,
        uow: IdentityUnitOfWork,
        password_hasher: IPasswordHasher,
        clock: IClock,
        *,
        verification_ttl_hours: int = 24,
        auto_verify_email: bool = False,
    ) -> None:
        self._uow = uow
        self._password_hasher = password_hasher
        self._clock = clock
        self._verification_ttl_hours = verification_ttl_hours
        self._auto_verify_email = auto_verify_email

    async def execute(self, command: RegisterUserCommand) -> User:
        existing = await self._uow.users.get_by_email(command.email)
        if existing is not None:
            raise EmailAlreadyRegisteredException(f"{command.email} is already registered")

        verification_token = secrets.token_urlsafe(32)
        user = User.register(
            email=EmailAddress(command.email),
            display_name=command.display_name,
            password_hash=self._password_hasher.hash(command.password),
            verification_token=verification_token,
            verification_expires_at=self._clock.now() + timedelta(hours=self._verification_ttl_hours),
        )
        if self._auto_verify_email:
            # Deployments that can't deliver the verification email set
            # AUTH_AUTO_VERIFY_EMAIL — run the user straight through the real
            # verify transition so login isn't walled off. UserRegistered
            # still fires; its email task is a harmless no-op here.
            user.verify_email(token=verification_token, now=self._clock.now())
        self._uow.users.add(user)
        await self._uow.commit()
        return user
