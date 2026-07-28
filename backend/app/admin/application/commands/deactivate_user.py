import uuid
from dataclasses import dataclass

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.identity.domain.entities import User
from app.identity.domain.exceptions import CannotDeactivateSelfException, UserNotFoundException


@dataclass(frozen=True)
class DeactivateUserCommand:
    user_id: uuid.UUID
    actor_user_id: uuid.UUID


class DeactivateUserUseCase:
    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: DeactivateUserCommand) -> User:
        if command.user_id == command.actor_user_id:
            raise CannotDeactivateSelfException("You cannot deactivate your own account")

        user = await self._uow.users.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException(f"User {command.user_id} not found")

        user.deactivate()
        await self._uow.users.update(user)
        await self._uow.commit()
        return user
