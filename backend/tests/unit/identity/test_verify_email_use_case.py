from datetime import timedelta

import pytest

from app.identity.application.commands.verify_email import VerifyEmailCommand, VerifyEmailUseCase
from app.identity.domain.entities import User
from app.identity.domain.exceptions import InvalidOrExpiredTokenException
from app.identity.domain.value_objects import EmailAddress
from tests.fakes.fake_ports import FakeClock
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


async def test_verify_email_use_case_marks_user_verified() -> None:
    uow = FakeUnitOfWork()
    clock = FakeClock()
    user = User.register(
        email=EmailAddress("owner@acme.com"),
        display_name="Ada Owner",
        password_hash="hashed:pw",
        verification_token="tok",
        verification_expires_at=clock.now() + timedelta(hours=24),
    )
    uow.users.add(user)

    verified = await VerifyEmailUseCase(uow, clock).execute(
        VerifyEmailCommand(user_id=user.id, token="tok")
    )

    assert verified.is_email_verified is True


async def test_verify_email_use_case_with_wrong_token_raises() -> None:
    uow = FakeUnitOfWork()
    clock = FakeClock()
    user = User.register(
        email=EmailAddress("owner@acme.com"),
        display_name="Ada Owner",
        password_hash="hashed:pw",
        verification_token="tok",
        verification_expires_at=clock.now() + timedelta(hours=24),
    )
    uow.users.add(user)

    with pytest.raises(InvalidOrExpiredTokenException):
        await VerifyEmailUseCase(uow, clock).execute(
            VerifyEmailCommand(user_id=user.id, token="wrong")
        )
