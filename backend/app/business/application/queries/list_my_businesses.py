import uuid
from dataclasses import dataclass

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.domain.entities import Business
from app.business.domain.value_objects import BusinessRole
from app.firms.application.access import combine
from app.firms.domain.value_objects import FirmStatus


@dataclass(frozen=True)
class ListMyBusinessesQuery:
    user_id: uuid.UUID


@dataclass(frozen=True)
class MyBusinessView:
    business: Business
    role: BusinessRole
    via_firm: bool = False
    firm_name: str | None = None


class ListMyBusinessesUseCase:
    """Drives the business switcher: every business the caller can open, paired
    with their effective role. That is the businesses they are a member of, plus
    every client business of an accounting firm they work for (their role there
    comes from their firm role; where both apply the stronger one wins).
    Cross-context (businesses + firms), so it takes the concrete AppUnitOfWork.
    """

    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListMyBusinessesQuery) -> list[MyBusinessView]:
        direct: dict[uuid.UUID, BusinessRole] = {}
        for membership in await self._uow.business_memberships.list_for_user(query.user_id):
            if membership.is_active:
                direct[membership.business_id] = membership.role

        views: dict[uuid.UUID, MyBusinessView] = {}
        for business_id, role in direct.items():
            business = await self._uow.businesses.get_by_id(business_id)
            if business is not None:
                views[business_id] = MyBusinessView(business=business, role=role)

        for firm_membership in await self._uow.firms.list_active_memberships_for_user(query.user_id):
            firm = await self._uow.firms.get_firm(firm_membership.firm_id)
            if firm is None or firm.status != FirmStatus.ACTIVE:
                continue
            for business in await self._uow.businesses.list_by_firm_id(firm.id):
                access = combine(direct.get(business.id), firm_membership.role)
                if access is not None:
                    views[business.id] = MyBusinessView(
                        business=business,
                        role=access.role,
                        via_firm=access.via_firm,
                        firm_name=firm.name,
                    )
        return list(views.values())
