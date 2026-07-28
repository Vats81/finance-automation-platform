import uuid
from dataclasses import dataclass

from app.business.application.ports import BusinessUnitOfWork
from app.business.domain.entities import Business
from app.business.domain.value_objects import BusinessRole


@dataclass(frozen=True)
class ListMyBusinessesQuery:
    user_id: uuid.UUID


@dataclass(frozen=True)
class MyBusinessView:
    business: Business
    role: BusinessRole


class ListMyBusinessesUseCase:
    """Drives the business switcher / 'manage multiple businesses ... from
    one account' — every active membership's business, paired with the
    caller's role in it.
    """

    def __init__(self, uow: BusinessUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListMyBusinessesQuery) -> list[MyBusinessView]:
        memberships = await self._uow.business_memberships.list_for_user(query.user_id)
        views: list[MyBusinessView] = []
        for membership in memberships:
            if not membership.is_active:
                continue
            business = await self._uow.businesses.get_by_id(membership.business_id)
            if business is not None:
                views.append(MyBusinessView(business=business, role=membership.role))
        return views
