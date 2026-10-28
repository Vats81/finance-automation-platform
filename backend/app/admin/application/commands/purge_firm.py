import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.infrastructure.models import BusinessModel
from app.firms.domain.exceptions import FirmNotFoundException
from app.firms.infrastructure.models import FirmMembershipModel, FirmModel
from app.shared.domain.exceptions import ConflictException, ValidationException

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PurgeFirmCommand:
    firm_id: uuid.UUID
    confirm_name: str
    actor_user_id: uuid.UUID


class PurgeFirmUseCase:
    """Permanently deletes an accounting firm and its staff memberships. Refuses while the
    firm still has client businesses: purge those first, so a firm's delete can never take
    a client's books with it. Requires the firm's exact name as confirmation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, command: PurgeFirmCommand) -> None:
        firm = await self._session.get(FirmModel, command.firm_id)
        if firm is None:
            raise FirmNotFoundException(f"Firm {command.firm_id} not found")
        if command.confirm_name.strip() != firm.name:
            raise ValidationException("Confirmation does not match the firm name; nothing was deleted.")

        clients = (
            await self._session.execute(
                select(func.count()).select_from(BusinessModel).where(BusinessModel.firm_id == firm.id)
            )
        ).scalar_one()
        if clients:
            raise ConflictException(
                f"This firm still has {clients} client business(es). Delete or release them first."
            )

        await self._session.execute(delete(FirmMembershipModel).where(FirmMembershipModel.firm_id == firm.id))
        await self._session.delete(firm)
        await self._session.commit()
        logger.warning(
            "Platform admin %s deleted firm %s (%s)", command.actor_user_id, command.firm_id, firm.name
        )
