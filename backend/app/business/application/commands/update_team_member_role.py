import uuid
from dataclasses import dataclass

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.domain.entities import BusinessMembership
from app.business.domain.exceptions import (
    BusinessNotFoundException,
    CannotChangeOwnRoleException,
    CannotModifyOwnerMembershipException,
    MembershipNotFoundException,
    OwnerRoleNotAssignableException,
)
from app.business.domain.value_objects import BusinessRole


@dataclass(frozen=True)
class UpdateTeamMemberRoleCommand:
    business_id: uuid.UUID
    membership_id: uuid.UUID
    role: BusinessRole
    actor_user_id: uuid.UUID


class UpdateTeamMemberRoleUseCase:
    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: UpdateTeamMemberRoleCommand) -> BusinessMembership:
        if command.role == BusinessRole.OWNER:
            raise OwnerRoleNotAssignableException("The Owner role cannot be granted to a team member.")

        business = await self._uow.businesses.get_by_id(command.business_id)
        if business is None:
            raise BusinessNotFoundException(f"Business {command.business_id} not found")

        membership = await self._uow.business_memberships.get_by_id(command.membership_id)
        if membership is None or membership.business_id != command.business_id:
            raise MembershipNotFoundException(f"Membership {command.membership_id} not found")

        if membership.user_id == business.owner_user_id or membership.role == BusinessRole.OWNER:
            raise CannotModifyOwnerMembershipException("The business owner's role cannot be changed.")
        if membership.user_id == command.actor_user_id:
            raise CannotChangeOwnRoleException("You cannot change your own role.")

        membership.change_role(role=command.role)
        await self._uow.business_memberships.update(membership)
        await self._uow.commit()
        return membership
