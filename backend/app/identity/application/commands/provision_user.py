from dataclasses import dataclass

from app.identity.application.ports import IdentityUnitOfWork
from app.identity.domain.entities import User
from app.identity.domain.value_objects import EmailAddress


@dataclass(frozen=True)
class ProvisionUserCommand:
    entra_object_id: str
    email: str
    display_name: str


class ProvisionUserUseCase:
    """JIT-provisions a User on first-seen Entra `oid` claim; idempotent for
    every subsequent login. Invoked from identity/api/dependencies.py's
    get_current_user on every authenticated request.
    """

    def __init__(self, uow: IdentityUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: ProvisionUserCommand) -> User:
        existing = await self._uow.users.get_by_entra_object_id(command.entra_object_id)
        if existing is not None:
            return existing

        user = User.provision(
            entra_object_id=command.entra_object_id,
            email=EmailAddress(command.email),
            display_name=command.display_name,
        )
        self._uow.users.add(user)
        await self._uow.commit()
        return user
