import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.infrastructure.models import BusinessMembershipModel, BusinessModel
from app.identity.domain.exceptions import UserNotFoundException
from app.identity.infrastructure.models import UserModel
from app.shared.domain.exceptions import ConflictException, ValidationException

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeleteUserCommand:
    user_id: uuid.UUID
    confirm_email: str
    actor_user_id: uuid.UUID


class DeleteUserUseCase:
    """Permanently deletes a user account and their memberships. Refuses to
    delete yourself, another platform admin, or an owner of a business that
    still exists — purge that business first, so no business is ever left with
    a dangling owner. Requires the user's exact email as confirmation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, command: DeleteUserCommand) -> None:
        if command.user_id == command.actor_user_id:
            raise ValidationException("You cannot delete your own account.")
        user = await self._session.get(UserModel, command.user_id)
        if user is None:
            raise UserNotFoundException(f"User {command.user_id} not found")
        if user.is_platform_admin:
            raise ValidationException("Platform admin accounts cannot be deleted here.")
        if command.confirm_email.strip().lower() != user.email.lower():
            raise ValidationException("Confirmation does not match the user's email; nothing was deleted.")

        owned = await self._session.execute(
            select(BusinessModel.name).where(BusinessModel.owner_user_id == user.id)
        )
        owned_names = [name for (name,) in owned.all()]
        if owned_names:
            raise ConflictException(
                f"This user owns {len(owned_names)} business(es) ({', '.join(owned_names[:3])}). "
                "Delete those businesses first."
            )

        await self._session.execute(
            delete(BusinessMembershipModel).where(BusinessMembershipModel.user_id == user.id)
        )
        await self._session.delete(user)
        await self._session.commit()
        logger.warning(
            "Platform admin %s deleted user %s (%s)", command.actor_user_id, command.user_id, user.email
        )
