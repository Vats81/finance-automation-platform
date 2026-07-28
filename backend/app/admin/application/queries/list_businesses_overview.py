import uuid
from dataclasses import dataclass
from datetime import datetime

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.domain.value_objects import BusinessPlan, BusinessStatus


@dataclass(frozen=True)
class ListBusinessesOverviewQuery:
    offset: int = 0
    limit: int = 50


@dataclass(frozen=True)
class BusinessOverviewItem:
    id: uuid.UUID
    name: str
    plan: BusinessPlan
    status: BusinessStatus
    member_count: int
    owner_email: str
    created_at: datetime


@dataclass(frozen=True)
class BusinessesOverviewPage:
    items: list[BusinessOverviewItem]
    total: int
    offset: int
    limit: int


class ListBusinessesOverviewUseCase:
    """Platform-wide, not business-scoped — the Admin Panel's one reason to
    exist. Cross-context by nature (businesses + business_memberships +
    users), same documented exception as every other admin/dashboard/
    notifications orchestration use case.
    """

    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListBusinessesOverviewQuery) -> BusinessesOverviewPage:
        businesses, total = await self._uow.businesses.list_all(offset=query.offset, limit=query.limit)

        items = []
        for business in businesses:
            memberships = await self._uow.business_memberships.list_for_business(business.id)
            member_count = sum(1 for m in memberships if m.is_active)
            owner = await self._uow.users.get_by_id(business.owner_user_id)
            items.append(
                BusinessOverviewItem(
                    id=business.id,
                    name=business.name,
                    plan=business.plan,
                    status=business.status,
                    member_count=member_count,
                    owner_email=str(owner.email) if owner else "",
                    created_at=business.created_at,
                )
            )

        return BusinessesOverviewPage(items=items, total=total, offset=query.offset, limit=query.limit)
