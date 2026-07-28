import uuid
from dataclasses import dataclass

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.domain.value_objects import BusinessRole, MembershipStatus


@dataclass(frozen=True)
class ListTeamMembersQuery:
    business_id: uuid.UUID


@dataclass(frozen=True)
class TeamMemberView:
    membership_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    display_name: str
    role: BusinessRole
    status: MembershipStatus


class ListTeamMembersUseCase:
    """Returns every membership for the business — active, invited, and
    removed — rather than hiding removed rows, matching this codebase's
    "never hide records, always show a status badge" convention already
    used for voided Sales/Purchases/Expenses.
    """

    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListTeamMembersQuery) -> list[TeamMemberView]:
        memberships = await self._uow.business_memberships.list_for_business(query.business_id)

        views = []
        for membership in memberships:
            user = await self._uow.users.get_by_id(membership.user_id)
            views.append(
                TeamMemberView(
                    membership_id=membership.id,
                    user_id=membership.user_id,
                    email=str(user.email) if user else "",
                    display_name=user.display_name if user else "",
                    role=membership.role,
                    status=membership.status,
                )
            )
        return views
