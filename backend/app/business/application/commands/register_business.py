import uuid
from dataclasses import dataclass

from app.business.application.ports import BusinessUnitOfWork
from app.business.domain.entities import Business, BusinessMembership
from app.business.domain.exceptions import PersonalWorkspaceExistsException
from app.business.domain.value_objects import BusinessKind, BusinessRole


@dataclass(frozen=True)
class RegisterBusinessCommand:
    owner_user_id: uuid.UUID
    name: str
    kind: BusinessKind = BusinessKind.BUSINESS
    firm_id: uuid.UUID | None = None
    currency: str = "USD"


class RegisterBusinessUseCase:
    """Creates the Business and its owner BusinessMembership in one
    transaction — two aggregates, one commit, the same deliberate exception
    to 'one aggregate per transaction' already used by
    StartApprovalWorkflowUseCase (both aggregates live in the same database;
    a single atomic commit is safer here than a second outbox hop that
    could leave the business ownerless if the process died in between).
    """

    def __init__(self, uow: BusinessUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: RegisterBusinessCommand) -> Business:
        if command.kind == BusinessKind.PERSONAL:
            for membership in await self._uow.business_memberships.list_for_user(command.owner_user_id):
                if membership.role != BusinessRole.OWNER or not membership.is_active:
                    continue
                existing = await self._uow.businesses.get_by_id(membership.business_id)
                if existing is not None and existing.kind == BusinessKind.PERSONAL:
                    raise PersonalWorkspaceExistsException(
                        "You already have a personal workspace. Each person has one."
                    )
        business = Business.register(
            owner_user_id=command.owner_user_id,
            name=command.name,
            kind=command.kind,
            firm_id=command.firm_id,
            currency=command.currency,
        )
        self._uow.businesses.add(business)

        membership = BusinessMembership.create_owner(business_id=business.id, user_id=command.owner_user_id)
        self._uow.business_memberships.add(membership)

        await self._uow.commit()
        return business
