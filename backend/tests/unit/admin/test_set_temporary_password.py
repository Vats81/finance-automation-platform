import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.admin.application.commands.set_temporary_password import (
    SetTemporaryPasswordCommand,
    SetTemporaryPasswordUseCase,
)
from app.identity.domain.entities import User
from app.identity.domain.exceptions import UserNotFoundException
from app.identity.domain.value_objects import EmailAddress
from app.shared.domain.exceptions import ValidationException
from tests.fakes.fake_ports import FakePasswordHasher
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

HASHER = FakePasswordHasher()
ADMIN = uuid.uuid4()


def _user(uow: FakeUnitOfWork) -> User:
    user = User.register(
        email=EmailAddress("tester@example.com"),
        display_name="Tester",
        password_hash=HASHER.hash("old-password"),
        verification_token="t",
        verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    uow.users.add(user)
    return user


async def test_the_user_gets_a_new_random_password_and_loses_the_old_one() -> None:
    uow = FakeUnitOfWork()
    user = _user(uow)
    user.request_password_reset(
        reset_token="link", expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )

    temporary = await SetTemporaryPasswordUseCase(uow, HASHER).execute(
        SetTemporaryPasswordCommand(user_id=user.id, actor_user_id=ADMIN)
    )

    stored = (await uow.users.get_by_id(user.id)).password_hash  # type: ignore[union-attr]
    assert len(temporary) >= 12
    assert HASHER.verify(temporary, stored)  # type: ignore[arg-type]
    assert not HASHER.verify("old-password", stored)  # type: ignore[arg-type]
    assert user.password_reset_token_hash is None  # a pending reset link is cancelled


async def test_each_call_gives_a_different_password() -> None:
    uow = FakeUnitOfWork()
    user = _user(uow)
    use_case = SetTemporaryPasswordUseCase(uow, HASHER)

    first = await use_case.execute(SetTemporaryPasswordCommand(user_id=user.id, actor_user_id=ADMIN))
    second = await use_case.execute(SetTemporaryPasswordCommand(user_id=user.id, actor_user_id=ADMIN))

    assert first != second


async def test_it_refuses_yourself_admins_and_accounts_without_a_password() -> None:
    uow = FakeUnitOfWork()
    user = _user(uow)
    use_case = SetTemporaryPasswordUseCase(uow, HASHER)

    with pytest.raises(ValidationException):
        await use_case.execute(SetTemporaryPasswordCommand(user_id=user.id, actor_user_id=user.id))

    user.is_platform_admin = True
    with pytest.raises(ValidationException):
        await use_case.execute(SetTemporaryPasswordCommand(user_id=user.id, actor_user_id=ADMIN))

    user.is_platform_admin = False
    user.password_hash = None
    with pytest.raises(ValidationException):
        await use_case.execute(SetTemporaryPasswordCommand(user_id=user.id, actor_user_id=ADMIN))


async def test_an_unknown_user_is_not_found() -> None:
    with pytest.raises(UserNotFoundException):
        await SetTemporaryPasswordUseCase(FakeUnitOfWork(), HASHER).execute(
            SetTemporaryPasswordCommand(user_id=uuid.uuid4(), actor_user_id=ADMIN)
        )
