import uuid
from dataclasses import dataclass

from app.identity.application.ports import IdentityUnitOfWork
from app.identity.domain.entities import User
from app.identity.domain.exceptions import UserNotFoundException
from app.shared.application.ports import IClock


@dataclass(frozen=True)
class VerifyEmailCommand:
    user_id: uuid.UUID
    token: str


class VerifyEmailUseCase:
    def __init__(self, uow: IdentityUnitOfWork, clock: IClock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, command: VerifyEmailCommand) -> User:
        user = await self._uow.users.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException(f"User {command.user_id} not found")

        user.verify_email(token=command.token, now=self._clock.now())
        await self._uow.users.update(user)
        await self._uow.commit()
        return user
