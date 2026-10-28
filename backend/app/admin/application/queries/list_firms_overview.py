import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.infrastructure.models import BusinessModel
from app.firms.infrastructure.models import FirmMembershipModel, FirmModel
from app.identity.infrastructure.models import UserModel


@dataclass(frozen=True)
class FirmOverviewItem:
    id: uuid.UUID
    name: str
    status: str
    owner_email: str
    staff_count: int
    client_count: int
    created_at: datetime


class ListFirmsOverviewUseCase:
    """Every firm on the platform with its owner and size, for the platform admin."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self) -> list[FirmOverviewItem]:
        staff = (
            select(FirmMembershipModel.firm_id, func.count().label("n"))
            .group_by(FirmMembershipModel.firm_id)
            .subquery()
        )
        clients = (
            select(BusinessModel.firm_id, func.count().label("n"))
            .where(BusinessModel.firm_id.is_not(None))
            .group_by(BusinessModel.firm_id)
            .subquery()
        )
        rows = await self._session.execute(
            select(
                FirmModel,
                UserModel.email,
                func.coalesce(staff.c.n, 0),
                func.coalesce(clients.c.n, 0),
            )
            .join(UserModel, UserModel.id == FirmModel.owner_user_id, isouter=True)
            .join(staff, staff.c.firm_id == FirmModel.id, isouter=True)
            .join(clients, clients.c.firm_id == FirmModel.id, isouter=True)
            .order_by(FirmModel.created_at.desc())
        )
        return [
            FirmOverviewItem(
                id=firm.id,
                name=firm.name,
                status=firm.status,
                owner_email=email or "",
                staff_count=int(staff_count),
                client_count=int(client_count),
                created_at=firm.created_at,
            )
            for firm, email, staff_count, client_count in rows.all()
        ]
