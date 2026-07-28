import secrets
from dataclasses import dataclass
from datetime import timedelta

from app.identity.application.ports import IdentityUnitOfWork
from app.identity.domain.value_objects import AuthProvider
from app.shared.application.ports import IClock


@dataclass(frozen=True)
class RequestPasswordResetCommand:
    email: str


class RequestPasswordResetUseCase:
    """Silently no-ops for unknown emails or non-LOCAL accounts, to avoid
    leaking which emails are registered — the API route always returns 204
    regardless of what happened here.
    """

    def __init__(self, uow: IdentityUnitOfWork, clock: IClock, *, reset_ttl_hours: int = 2) -> None:
        self._uow = uow
        self._clock = clock
        self._reset_ttl_hours = reset_ttl_hours

    async def execute(self, command: RequestPasswordResetCommand) -> None:
        user = await self._uow.users.get_by_email(command.email)
        if user is None or user.auth_provider != AuthProvider.LOCAL:
            return

        reset_token = secrets.token_urlsafe(32)
        user.request_password_reset(
            reset_token=reset_token,
            expires_at=self._clock.now() + timedelta(hours=self._reset_ttl_hours),
        )
        await self._uow.users.update(user)
        await self._uow.commit()
