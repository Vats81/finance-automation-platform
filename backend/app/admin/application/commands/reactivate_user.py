import uuid
from dataclasses import dataclass

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.identity.domain.entities import User
from app.identity.domain.exceptions import UserNotFoundException


@dataclass(frozen=True)
class ReactivateUserCommand:
    user_id: uuid.UUID


class ReactivateUserUseCase:
    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: ReactivateUserCommand) -> User:
        user = await self._uow.users.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException(f"User {command.user_id} not found")

        user.reactivate()
        await self._uow.users.update(user)
        await self._uow.commit()
        return user
