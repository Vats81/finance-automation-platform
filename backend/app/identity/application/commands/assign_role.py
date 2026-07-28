import uuid
from dataclasses import dataclass

from app.identity.application.ports import IdentityUnitOfWork
from app.identity.domain.entities import User
from app.identity.domain.exceptions import UserNotFoundException
from app.identity.domain.value_objects import Role


@dataclass(frozen=True)
class AssignRoleCommand:
    target_user_id: uuid.UUID
    new_role: Role
    actor_user_id: uuid.UUID


class AssignRoleUseCase:
    """Only reachable via the /users admin endpoint, itself gated by
    require_role(Role.FINANCE_ADMIN) at the API boundary.
    """

    def __init__(self, uow: IdentityUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: AssignRoleCommand) -> User:
        user = await self._uow.users.get_by_id(command.target_user_id)
        if user is None:
            raise UserNotFoundException(f"User {command.target_user_id} not found")

        user.change_role(new_role=command.new_role, changed_by_user_id=command.actor_user_id)
        await self._uow.users.update(user)
        await self._uow.commit()
        return user
