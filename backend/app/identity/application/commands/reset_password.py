import uuid
from dataclasses import dataclass

from app.identity.application.ports import IdentityUnitOfWork
from app.identity.domain.entities import User
from app.identity.domain.exceptions import UserNotFoundException
from app.shared.application.ports import IClock, IPasswordHasher


@dataclass(frozen=True)
class ResetPasswordCommand:
    user_id: uuid.UUID
    token: str
    new_password: str


class ResetPasswordUseCase:
    def __init__(self, uow: IdentityUnitOfWork, password_hasher: IPasswordHasher, clock: IClock) -> None:
        self._uow = uow
        self._password_hasher = password_hasher
        self._clock = clock

    async def execute(self, command: ResetPasswordCommand) -> User:
        user = await self._uow.users.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException(f"User {command.user_id} not found")

        user.reset_password(
            token=command.token,
            new_password_hash=self._password_hasher.hash(command.new_password),
            now=self._clock.now(),
        )
        await self._uow.users.update(user)
        await self._uow.commit()
        return user
