import uuid
from dataclasses import dataclass

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.application.plan_limits import PLAN_LIMITS
from app.business.domain.entities import BusinessMembership
from app.business.domain.exceptions import (
    BusinessNotFoundException,
    InviteeNotRegisteredException,
    TeamMemberLimitExceededException,
    UserAlreadyMemberException,
)
from app.business.domain.value_objects import BusinessRole
from app.shared.application.ports import IEmailSender


@dataclass(frozen=True)
class InviteTeamMemberCommand:
    business_id: uuid.UUID
    invited_by_user_id: uuid.UUID
    email: str
    role: BusinessRole


class InviteTeamMemberUseCase:
    """Cross-context by nature (businesses + business_memberships + users),
    so this takes the concrete AppUnitOfWork rather than the narrower
    BusinessUnitOfWork Protocol — same documented exception already used
    by dashboard/ai_assistant/notifications for orchestration use cases.
    """

    def __init__(self, uow: AppUnitOfWork, email_sender: IEmailSender) -> None:
        self._uow = uow
        self._email_sender = email_sender

    async def execute(self, command: InviteTeamMemberCommand) -> BusinessMembership:
        business = await self._uow.businesses.get_by_id(command.business_id)
        if business is None:
            raise BusinessNotFoundException(f"Business {command.business_id} not found")

        existing_members = await self._uow.business_memberships.list_for_business(command.business_id)
        active_count = sum(1 for m in existing_members if m.is_active)
        limit = PLAN_LIMITS[business.plan].max_team_members
        if active_count >= limit:
            raise TeamMemberLimitExceededException(
                f"This business's {business.plan.value} plan allows up to {limit} team members. "
                "Upgrade the plan to invite more."
            )

        invitee = await self._uow.users.get_by_email(command.email)
        if invitee is None:
            raise InviteeNotRegisteredException(
                f"No FinanceAI account found for {command.email}. Ask them to sign up first, then "
                "invite them by the same email."
            )

        if any(m.user_id == invitee.id and m.is_active for m in existing_members):
            raise UserAlreadyMemberException(f"{command.email} is already a member of this business.")

        membership = BusinessMembership.invite(
            business_id=business.id,
            user_id=invitee.id,
            role=command.role,
            invited_by_user_id=command.invited_by_user_id,
        )
        self._uow.business_memberships.add(membership)
        await self._uow.commit()

        await self._email_sender.send(
            to=command.email,
            subject=f"You've been added to {business.name} on FinanceAI",
            body=(
                f"You've been added to {business.name} as a {command.role.value}. "
                "Log in to FinanceAI to get started."
            ),
        )
        return membership
