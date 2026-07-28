from datetime import datetime, timedelta, timezone

import pytest

from app.config.settings import get_settings
from app.identity.application.commands.login_user import LoginUserCommand, LoginUserUseCase
from app.identity.domain.entities import User
from app.identity.domain.exceptions import EmailNotVerifiedException, InvalidCredentialsException
from app.identity.domain.value_objects import EmailAddress
from app.identity.infrastructure.local_auth.token_issuer import LocalTokenIssuer
from tests.fakes.fake_ports import FakePasswordHasher
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


def make_use_case(uow: FakeUnitOfWork) -> LoginUserUseCase:
    return LoginUserUseCase(uow, FakePasswordHasher(), LocalTokenIssuer(get_settings()))


async def seed_verified_user(
    uow: FakeUnitOfWork, *, email: str = "owner@acme.com", password: str = "pw"
) -> User:
    hasher = FakePasswordHasher()
    user = User.register(
        email=EmailAddress(email),
        display_name="Ada Owner",
        password_hash=hasher.hash(password),
        verification_token="tok",
        verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    user.verify_email(token="tok", now=datetime.now(timezone.utc))
    uow.users.add(user)
    return user


async def test_login_with_correct_credentials_issues_token() -> None:
    uow = FakeUnitOfWork()
    await seed_verified_user(uow, email="owner@acme.com", password="s3cret")

    result = await make_use_case(uow).execute(LoginUserCommand(email="owner@acme.com", password="s3cret"))

    assert result.user.email == EmailAddress("owner@acme.com")
    assert result.access_token
    assert result.expires_at > datetime.now(timezone.utc)


async def test_login_with_wrong_password_raises() -> None:
    uow = FakeUnitOfWork()
    await seed_verified_user(uow, email="owner@acme.com", password="s3cret")

    with pytest.raises(InvalidCredentialsException):
        await make_use_case(uow).execute(LoginUserCommand(email="owner@acme.com", password="wrong"))


async def test_login_unknown_email_raises_invalid_credentials() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(InvalidCredentialsException):
        await make_use_case(uow).execute(LoginUserCommand(email="nobody@acme.com", password="anything"))


async def test_login_before_email_verified_raises() -> None:
    uow = FakeUnitOfWork()
    hasher = FakePasswordHasher()
    user = User.register(
        email=EmailAddress("unverified@acme.com"),
        display_name="Unverified",
        password_hash=hasher.hash("s3cret"),
        verification_token="tok",
        verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    uow.users.add(user)

    with pytest.raises(EmailNotVerifiedException):
        await make_use_case(uow).execute(LoginUserCommand(email="unverified@acme.com", password="s3cret"))
