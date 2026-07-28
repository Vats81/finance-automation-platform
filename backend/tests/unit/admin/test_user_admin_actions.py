import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.admin.application.commands.deactivate_user import DeactivateUserCommand, DeactivateUserUseCase
from app.admin.application.commands.reactivate_user import ReactivateUserCommand, ReactivateUserUseCase
from app.identity.domain.entities import User
from app.identity.domain.exceptions import CannotDeactivateSelfException
from app.identity.domain.value_objects import EmailAddress
from tests.fakes.fake_ports import FakePasswordHasher
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


async def test_deactivate_user_sets_inactive() -> None:
    uow = FakeUnitOfWork()
    admin_id = uuid.uuid4()
    user = seed_user(uow, "teammate@example.com")

    deactivated = await DeactivateUserUseCase(uow).execute(
        DeactivateUserCommand(user_id=user.id, actor_user_id=admin_id)
    )

    assert deactivated.is_active is False


async def test_deactivate_user_blocked_when_targeting_self() -> None:
    uow = FakeUnitOfWork()
    admin = seed_user(uow, "admin@example.com")

    with pytest.raises(CannotDeactivateSelfException):
        await DeactivateUserUseCase(uow).execute(
            DeactivateUserCommand(user_id=admin.id, actor_user_id=admin.id)
        )


async def test_reactivate_user_sets_active() -> None:
    uow = FakeUnitOfWork()
    admin_id = uuid.uuid4()
    user = seed_user(uow, "teammate@example.com")
    await DeactivateUserUseCase(uow).execute(
        DeactivateUserCommand(user_id=user.id, actor_user_id=admin_id)
    )

    reactivated = await ReactivateUserUseCase(uow).execute(ReactivateUserCommand(user_id=user.id))

    assert reactivated.is_active is True
