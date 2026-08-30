import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.domain.entities import Business, BusinessMembership
from app.business.domain.exceptions import BusinessNotFoundException
from app.business.domain.repository import IBusinessMembershipRepository, IBusinessRepository
from app.business.infrastructure.mappers import (
    apply_business_domain_to_existing_model,
    apply_membership_domain_to_existing_model,
    business_domain_to_model,
    business_model_to_domain,
    membership_domain_to_model,
    membership_model_to_domain,
)
from app.business.infrastructure.models import BusinessMembershipModel, BusinessModel
from app.shared.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemyBusinessRepository(IBusinessRepository):
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> AsyncSession:
        return self._uow.session

    async def get_by_id(self, business_id: uuid.UUID) -> Business | None:
        model = await self._session.get(BusinessModel, business_id)
        return business_model_to_domain(model) if model else None

    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[Business], int]:
        total = (await self._session.execute(select(func.count()).select_from(BusinessModel))).scalar_one()
        stmt = select(BusinessModel).order_by(BusinessModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        businesses = [business_model_to_domain(m) for m in result.scalars().all()]
        return businesses, total

    async def get_by_stripe_subscription_id(self, subscription_id: str) -> Business | None:
        stmt = select(BusinessModel).where(BusinessModel.stripe_subscription_id == subscription_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return business_model_to_domain(model) if model else None

    def add(self, business: Business) -> None:
        self._session.add(business_domain_to_model(business))
        self._uow.collect_events(business)

    async def update(self, business: Business) -> None:
        model = await self._session.get(BusinessModel, business.id)
        if model is None:
            raise BusinessNotFoundException(f"Business {business.id} not found")
        apply_business_domain_to_existing_model(business, model)
        self._uow.collect_events(business)


class SqlAlchemyBusinessMembershipRepository(IBusinessMembershipRepository):
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> AsyncSession:
        return self._uow.session

    async def get_by_id(self, membership_id: uuid.UUID) -> BusinessMembership | None:
        model = await self._session.get(BusinessMembershipModel, membership_id)
        return membership_model_to_domain(model) if model else None

    async def get_for_user_and_business(
        self, *, user_id: uuid.UUID, business_id: uuid.UUID
    ) -> BusinessMembership | None:
        stmt = select(BusinessMembershipModel).where(
            BusinessMembershipModel.user_id == user_id,
            BusinessMembershipModel.business_id == business_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return membership_model_to_domain(model) if model else None

    async def list_for_user(self, user_id: uuid.UUID) -> list[BusinessMembership]:
        stmt = select(BusinessMembershipModel).where(BusinessMembershipModel.user_id == user_id)
        result = await self._session.execute(stmt)
        return [membership_model_to_domain(m) for m in result.scalars().all()]

    async def list_for_business(self, business_id: uuid.UUID) -> list[BusinessMembership]:
        stmt = select(BusinessMembershipModel).where(BusinessMembershipModel.business_id == business_id)
        result = await self._session.execute(stmt)
        return [membership_model_to_domain(m) for m in result.scalars().all()]

    def add(self, membership: BusinessMembership) -> None:
        self._session.add(membership_domain_to_model(membership))
        self._uow.collect_events(membership)

    async def update(self, membership: BusinessMembership) -> None:
        model = await self._session.get(BusinessMembershipModel, membership.id)
        if model is None:
            raise BusinessNotFoundException(f"BusinessMembership {membership.id} not found")
        apply_membership_domain_to_existing_model(membership, model)
        self._uow.collect_events(membership)
