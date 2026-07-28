import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.business.application.commands.invite_team_member import (
    InviteTeamMemberCommand,
    InviteTeamMemberUseCase,
)
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.application.commands.remove_team_member import (
    RemoveTeamMemberCommand,
    RemoveTeamMemberUseCase,
)
from app.business.application.commands.update_team_member_role import (
    UpdateTeamMemberRoleCommand,
    UpdateTeamMemberRoleUseCase,
)
from app.business.application.queries.list_team_members import ListTeamMembersQuery, ListTeamMembersUseCase
from app.business.domain.exceptions import CannotModifyOwnerMembershipException
from app.business.domain.value_objects import BusinessRole, MembershipStatus
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


async def setup_business_with_member(uow: FakeUnitOfWork) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    owner_id = uuid.uuid4()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=owner_id, name="Acme")
    )
    seed_user(uow, "teammate@example.com")
    membership = await InviteTeamMemberUseCase(uow, FakeEmailSender()).execute(
        InviteTeamMemberCommand(
            business_id=business.id,
            invited_by_user_id=owner_id,
            email="teammate@example.com",
            role=BusinessRole.VIEWER,
        )
    )
    return business.id, owner_id, membership.id


async def test_remove_team_member_succeeds() -> None:
    uow = FakeUnitOfWork()
    business_id, _owner_id, membership_id = await setup_business_with_member(uow)

    removed = await RemoveTeamMemberUseCase(uow).execute(
        RemoveTeamMemberCommand(business_id=business_id, membership_id=membership_id)
    )

    assert removed.status == MembershipStatus.REMOVED


async def test_remove_team_member_blocked_for_owner() -> None:
    uow = FakeUnitOfWork()
    business_id, owner_id, _membership_id = await setup_business_with_member(uow)
    owner_membership = await uow.business_memberships.get_for_user_and_business(
        user_id=owner_id, business_id=business_id
    )
    assert owner_membership is not None

    with pytest.raises(CannotModifyOwnerMembershipException):
        await RemoveTeamMemberUseCase(uow).execute(
            RemoveTeamMemberCommand(business_id=business_id, membership_id=owner_membership.id)
        )


async def test_update_team_member_role_succeeds() -> None:
    uow = FakeUnitOfWork()
    business_id, _owner_id, membership_id = await setup_business_with_member(uow)

    updated = await UpdateTeamMemberRoleUseCase(uow).execute(
        UpdateTeamMemberRoleCommand(
            business_id=business_id, membership_id=membership_id, role=BusinessRole.ADMIN
        )
    )

    assert updated.role == BusinessRole.ADMIN


async def test_update_team_member_role_blocked_for_owner() -> None:
    uow = FakeUnitOfWork()
    business_id, owner_id, _membership_id = await setup_business_with_member(uow)
    owner_membership = await uow.business_memberships.get_for_user_and_business(
        user_id=owner_id, business_id=business_id
    )
    assert owner_membership is not None

    with pytest.raises(CannotModifyOwnerMembershipException):
        await UpdateTeamMemberRoleUseCase(uow).execute(
            UpdateTeamMemberRoleCommand(
                business_id=business_id, membership_id=owner_membership.id, role=BusinessRole.VIEWER
            )
        )


async def test_list_team_members_returns_all_statuses_with_resolved_user_info() -> None:
    uow = FakeUnitOfWork()
    business_id, owner_id, membership_id = await setup_business_with_member(uow)
    await RemoveTeamMemberUseCase(uow).execute(
        RemoveTeamMemberCommand(business_id=business_id, membership_id=membership_id)
    )

    views = await ListTeamMembersUseCase(uow).execute(ListTeamMembersQuery(business_id=business_id))

    assert len(views) == 2
    owner_view = next(v for v in views if v.user_id == owner_id)
    assert owner_view.role == BusinessRole.OWNER
    assert owner_view.status == MembershipStatus.ACTIVE
    removed_view = next(v for v in views if v.membership_id == membership_id)
    assert removed_view.status == MembershipStatus.REMOVED
    assert removed_view.email == "teammate@example.com"
