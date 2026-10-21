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
from app.business.domain.exceptions import (
    CannotChangeOwnRoleException,
    CannotModifyOwnerMembershipException,
    MembershipNotFoundException,
    OwnerRoleNotAssignableException,
)
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
    business_id, owner_id, membership_id = await setup_business_with_member(uow)

    updated = await UpdateTeamMemberRoleUseCase(uow).execute(
        UpdateTeamMemberRoleCommand(
            business_id=business_id,
            membership_id=membership_id,
            role=BusinessRole.ADMIN,
            actor_user_id=owner_id,
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
                business_id=business_id,
                membership_id=owner_membership.id,
                role=BusinessRole.VIEWER,
                actor_user_id=uuid.uuid4(),
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


async def test_owner_role_cannot_be_granted_through_a_role_change() -> None:
    uow = FakeUnitOfWork()
    business_id, owner_id, membership_id = await setup_business_with_member(uow)

    with pytest.raises(OwnerRoleNotAssignableException):
        await UpdateTeamMemberRoleUseCase(uow).execute(
            UpdateTeamMemberRoleCommand(
                business_id=business_id,
                membership_id=membership_id,
                role=BusinessRole.OWNER,
                actor_user_id=owner_id,
            )
        )


async def test_a_member_cannot_change_their_own_role() -> None:
    uow = FakeUnitOfWork()
    business_id, _owner_id, membership_id = await setup_business_with_member(uow)
    membership = await uow.business_memberships.get_by_id(membership_id)
    assert membership is not None

    with pytest.raises(CannotChangeOwnRoleException):
        await UpdateTeamMemberRoleUseCase(uow).execute(
            UpdateTeamMemberRoleCommand(
                business_id=business_id,
                membership_id=membership_id,
                role=BusinessRole.ADMIN,
                actor_user_id=membership.user_id,
            )
        )


async def test_a_membership_from_another_business_cannot_be_changed_or_removed() -> None:
    uow = FakeUnitOfWork()
    _business_a, owner_a, membership_in_a = await setup_business_with_member(uow)
    business_b, _owner_b, _member_b = await setup_business_with_member(uow)

    with pytest.raises(MembershipNotFoundException):
        await UpdateTeamMemberRoleUseCase(uow).execute(
            UpdateTeamMemberRoleCommand(
                business_id=business_b,
                membership_id=membership_in_a,
                role=BusinessRole.VIEWER,
                actor_user_id=owner_a,
            )
        )
    with pytest.raises(MembershipNotFoundException):
        await RemoveTeamMemberUseCase(uow).execute(
            RemoveTeamMemberCommand(business_id=business_b, membership_id=membership_in_a)
        )


async def test_inviting_someone_as_owner_is_rejected() -> None:
    uow = FakeUnitOfWork()
    owner_id = uuid.uuid4()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=owner_id, name="Acme")
    )
    seed_user(uow, "wannabe@example.com")

    with pytest.raises(OwnerRoleNotAssignableException):
        await InviteTeamMemberUseCase(uow, FakeEmailSender()).execute(
            InviteTeamMemberCommand(
                business_id=business.id,
                invited_by_user_id=owner_id,
                email="wannabe@example.com",
                role=BusinessRole.OWNER,
            )
        )


async def test_a_removed_member_can_be_invited_again_and_gets_access_back() -> None:
    uow = FakeUnitOfWork()
    business_id, owner_id, membership_id = await setup_business_with_member(uow)
    await RemoveTeamMemberUseCase(uow).execute(
        RemoveTeamMemberCommand(business_id=business_id, membership_id=membership_id)
    )

    again = await InviteTeamMemberUseCase(uow, FakeEmailSender()).execute(
        InviteTeamMemberCommand(
            business_id=business_id,
            invited_by_user_id=owner_id,
            email="teammate@example.com",
            role=BusinessRole.ACCOUNTANT,
        )
    )

    assert again.is_active
    assert again.role == BusinessRole.ACCOUNTANT
