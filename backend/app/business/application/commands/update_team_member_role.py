import uuid
from dataclasses import dataclass

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.domain.entities import BusinessMembership
from app.business.domain.exceptions import (
    BusinessNotFoundException,
    CannotModifyOwnerMembershipException,
    MembershipNotFoundException,
)
from app.business.domain.value_objects import BusinessRole


@dataclass(frozen=True)
class UpdateTeamMemberRoleCommand:
    business_id: uuid.UUID
    membership_id: uuid.UUID
    role: BusinessRole


class UpdateTeamMemberRoleUseCase:
    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: UpdateTeamMemberRoleCommand) -> BusinessMembership:
        business = await self._uow.businesses.get_by_id(command.business_id)
        if business is None:
            raise BusinessNotFoundException(f"Business {command.business_id} not found")

        membership = await self._uow.business_memberships.get_by_id(command.membership_id)
        if membership is None or membership.business_id != command.business_id:
            raise MembershipNotFoundException(f"Membership {command.membership_id} not found")

        if membership.user_id == business.owner_user_id:
            raise CannotModifyOwnerMembershipException("The business owner's role cannot be changed.")

        membership.change_role(role=command.role)
        await self._uow.business_memberships.update(membership)
        await self._uow.commit()
        return membership
