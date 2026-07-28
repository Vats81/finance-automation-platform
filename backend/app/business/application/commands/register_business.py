import uuid
from dataclasses import dataclass

from app.business.application.ports import BusinessUnitOfWork
from app.business.domain.entities import Business, BusinessMembership


@dataclass(frozen=True)
class RegisterBusinessCommand:
    owner_user_id: uuid.UUID
    name: str


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
        business = Business.register(owner_user_id=command.owner_user_id, name=command.name)
        self._uow.businesses.add(business)

        membership = BusinessMembership.create_owner(business_id=business.id, user_id=command.owner_user_id)
        self._uow.business_memberships.add(membership)

        await self._uow.commit()
        return business
