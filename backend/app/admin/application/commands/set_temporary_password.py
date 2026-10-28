import logging
import secrets
import uuid
from dataclasses import dataclass

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.identity.domain.exceptions import UserNotFoundException
from app.shared.application.ports import IPasswordHasher
from app.shared.domain.exceptions import ValidationException

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SetTemporaryPasswordCommand:
    user_id: uuid.UUID
    actor_user_id: uuid.UUID


class SetTemporaryPasswordUseCase:
    """Gives a locked-out user a new random password, returned once to the platform admin to pass
    on (the self-serve reset needs working email). Refuses yourself, other platform admins and
    accounts without a local password. The password is never logged or stored in plain text, and
    any pending reset link is cancelled. Sessions the user already holds stay valid until they
    expire; deactivate the account first if that matters.
    """

    def __init__(self, uow: AppUnitOfWork, hasher: IPasswordHasher) -> None:
        self._uow = uow
        self._hasher = hasher

    async def execute(self, command: SetTemporaryPasswordCommand) -> str:
        if command.user_id == command.actor_user_id:
            raise ValidationException("Change your own password from your account, not here.")
        user = await self._uow.users.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException(f"User {command.user_id} not found")
        if user.is_platform_admin:
            raise ValidationException("Platform admin passwords cannot be reset here.")
        if user.password_hash is None:
            raise ValidationException("This account signs in elsewhere and has no password to reset.")

        temporary = secrets.token_urlsafe(12)
        user.set_password(self._hasher.hash(temporary))
        await self._uow.users.update(user)
        await self._uow.commit()
        logger.warning(
            "Platform admin %s set a temporary password for user %s", command.actor_user_id, user.id
        )
        return temporary
