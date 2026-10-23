import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.infrastructure.models import BusinessAuditEventModel
from app.firms.application.ports import FirmMemberRecord, FirmRecord, IFirmRepository
from app.firms.domain.value_objects import FirmMembershipStatus, FirmRole, FirmStatus
from app.firms.infrastructure.models import FirmMembershipModel, FirmModel
from app.shared.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


def _firm(m: FirmModel) -> FirmRecord:
    return FirmRecord(
        id=m.id,
        name=m.name,
        owner_user_id=m.owner_user_id,
        status=FirmStatus(m.status),
        created_at=m.created_at,
    )


def _member(m: FirmMembershipModel) -> FirmMemberRecord:
    return FirmMemberRecord(
        id=m.id,
        firm_id=m.firm_id,
        user_id=m.user_id,
        role=FirmRole(m.role),
        status=FirmMembershipStatus(m.status),
        invited_by_user_id=m.invited_by_user_id,
        joined_at=m.joined_at,
    )


class SqlAlchemyFirmRepository(IFirmRepository):
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> AsyncSession:
        return self._uow.session

    async def create_firm(self, *, name: str, owner_user_id: uuid.UUID) -> FirmRecord:
        firm = FirmModel(
            id=uuid.uuid4(), name=name, owner_user_id=owner_user_id, status=FirmStatus.ACTIVE.value
        )
        self._session.add(firm)
        self._session.add(
            FirmMembershipModel(
                id=uuid.uuid4(),
                firm_id=firm.id,
                user_id=owner_user_id,
                role=FirmRole.OWNER.value,
                status=FirmMembershipStatus.ACTIVE.value,
                joined_at=datetime.now(timezone.utc),
            )
        )
        await self._session.flush()
        await self._session.refresh(firm)
        return _firm(firm)

    async def get_firm(self, firm_id: uuid.UUID) -> FirmRecord | None:
        model = await self._session.get(FirmModel, firm_id)
        return _firm(model) if model else None

    async def get_membership(self, firm_id: uuid.UUID, user_id: uuid.UUID) -> FirmMemberRecord | None:
        result = await self._session.execute(
            select(FirmMembershipModel).where(
                FirmMembershipModel.firm_id == firm_id, FirmMembershipModel.user_id == user_id
            )
        )
        model = result.scalar_one_or_none()
        return _member(model) if model else None

    async def get_membership_by_id(self, membership_id: uuid.UUID) -> FirmMemberRecord | None:
        model = await self._session.get(FirmMembershipModel, membership_id)
        return _member(model) if model else None

    async def list_active_memberships_for_user(self, user_id: uuid.UUID) -> list[FirmMemberRecord]:
        result = await self._session.execute(
            select(FirmMembershipModel).where(
                FirmMembershipModel.user_id == user_id,
                FirmMembershipModel.status == FirmMembershipStatus.ACTIVE.value,
            )
        )
        return [_member(m) for m in result.scalars().all()]

    async def list_members(self, firm_id: uuid.UUID) -> list[FirmMemberRecord]:
        result = await self._session.execute(
            select(FirmMembershipModel)
            .where(FirmMembershipModel.firm_id == firm_id)
            .order_by(FirmMembershipModel.created_at)
        )
        return [_member(m) for m in result.scalars().all()]

    async def add_member(
        self, *, firm_id: uuid.UUID, user_id: uuid.UUID, role: FirmRole, invited_by_user_id: uuid.UUID
    ) -> FirmMemberRecord:
        model = FirmMembershipModel(
            id=uuid.uuid4(),
            firm_id=firm_id,
            user_id=user_id,
            role=role.value,
            status=FirmMembershipStatus.ACTIVE.value,
            invited_by_user_id=invited_by_user_id,
            joined_at=datetime.now(timezone.utc),
        )
        self._session.add(model)
        await self._session.flush()
        return _member(model)

    async def update_member(
        self,
        membership_id: uuid.UUID,
        *,
        role: FirmRole | None = None,
        status: FirmMembershipStatus | None = None,
        invited_by_user_id: uuid.UUID | None = None,
    ) -> FirmMemberRecord | None:
        model = await self._session.get(FirmMembershipModel, membership_id)
        if model is None:
            return None
        if role is not None:
            model.role = role.value
        if status is not None:
            model.status = status.value
            if status == FirmMembershipStatus.ACTIVE:
                model.joined_at = datetime.now(timezone.utc)
        if invited_by_user_id is not None:
            model.invited_by_user_id = invited_by_user_id
        await self._session.flush()
        return _member(model)

    async def last_activity_by_business(self, business_ids: list[uuid.UUID]) -> dict[uuid.UUID, datetime]:
        if not business_ids:
            return {}
        result = await self._session.execute(
            select(BusinessAuditEventModel.business_id, func.max(BusinessAuditEventModel.occurred_at))
            .where(BusinessAuditEventModel.business_id.in_(business_ids))
            .group_by(BusinessAuditEventModel.business_id)
        )
        return {business_id: when for business_id, when in result.all()}
