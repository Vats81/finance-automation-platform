import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.business.application.commands.change_business_plan import (
    ChangeBusinessPlanCommand,
    ChangeBusinessPlanUseCase,
)
from app.business.application.commands.invite_team_member import (
    InviteTeamMemberCommand,
    InviteTeamMemberUseCase,
)
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.domain.exceptions import (
    InviteeNotRegisteredException,
    TeamMemberLimitExceededException,
    UserAlreadyMemberException,
)
from app.business.domain.value_objects import BusinessPlan, BusinessRole
from app.identity.domain.entities import User
from app.identity.domain.value_objects import EmailAddress
from tests.fakes.fake_ports import FakeEmailSender, FakePasswordHasher
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


def seed_user(uow: FakeUnitOfWork, email: str) -> User:
    hasher = FakePasswordHasher()
    user = User.register(
        email=EmailAddress(email),
        display_name="Test User",
        password_hash=hasher.hash("pw"),
        verification_token="tok",
        verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    uow.users.add(user)
    return user


async def test_successful_invite_creates_active_membership_and_sends_email() -> None:
    uow = FakeUnitOfWork()
    owner_id = uuid.uuid4()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=owner_id, name="Acme")
    )
    invitee = seed_user(uow, "teammate@example.com")
    email_sender = FakeEmailSender()

    membership = await InviteTeamMemberUseCase(uow, email_sender).execute(
        InviteTeamMemberCommand(
            business_id=business.id,
            invited_by_user_id=owner_id,
            email="teammate@example.com",
            role=BusinessRole.ACCOUNTANT,
        )
    )

    assert membership.user_id == invitee.id
    assert membership.is_active is True
    assert len(email_sender.sent) == 1
    assert email_sender.sent[0]["to"] == "teammate@example.com"


async def test_invite_blocked_at_plan_member_limit() -> None:
    uow = FakeUnitOfWork()
    owner_id = uuid.uuid4()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=owner_id, name="Acme")
    )
    # Free plan allows 2 members; the owner already counts as 1, so one more
    # invite succeeds and a second should be blocked.
    seed_user(uow, "first@example.com")
    seed_user(uow, "second@example.com")

    await InviteTeamMemberUseCase(uow, FakeEmailSender()).execute(
        InviteTeamMemberCommand(
            business_id=business.id,
            invited_by_user_id=owner_id,
            email="first@example.com",
            role=BusinessRole.VIEWER,
        )
    )

    with pytest.raises(TeamMemberLimitExceededException):
        await InviteTeamMemberUseCase(uow, FakeEmailSender()).execute(
            InviteTeamMemberCommand(
                business_id=business.id,
                invited_by_user_id=owner_id,
                email="second@example.com",
                role=BusinessRole.VIEWER,
            )
        )


async def test_invite_blocked_when_invitee_not_registered() -> None:
    uow = FakeUnitOfWork()
    owner_id = uuid.uuid4()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=owner_id, name="Acme")
    )

    with pytest.raises(InviteeNotRegisteredException):
        await InviteTeamMemberUseCase(uow, FakeEmailSender()).execute(
            InviteTeamMemberCommand(
                business_id=business.id,
                invited_by_user_id=owner_id,
                email="nobody@example.com",
                role=BusinessRole.VIEWER,
            )
        )


async def test_invite_blocked_when_already_an_active_member() -> None:
    uow = FakeUnitOfWork()
    owner_id = uuid.uuid4()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=owner_id, name="Acme")
    )
    await ChangeBusinessPlanUseCase(uow).execute(
        ChangeBusinessPlanCommand(business_id=business.id, plan=BusinessPlan.PRO)
    )
    seed_user(uow, "teammate@example.com")
    await InviteTeamMemberUseCase(uow, FakeEmailSender()).execute(
        InviteTeamMemberCommand(
            business_id=business.id,
            invited_by_user_id=owner_id,
            email="teammate@example.com",
            role=BusinessRole.VIEWER,
        )
    )

    with pytest.raises(UserAlreadyMemberException):
        await InviteTeamMemberUseCase(uow, FakeEmailSender()).execute(
            InviteTeamMemberCommand(
                business_id=business.id,
                invited_by_user_id=owner_id,
                email="teammate@example.com",
                role=BusinessRole.ADMIN,
            )
        )
