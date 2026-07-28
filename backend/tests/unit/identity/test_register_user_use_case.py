import pytest

from app.identity.application.commands.register_user import RegisterUserCommand, RegisterUserUseCase
from app.identity.domain.exceptions import EmailAlreadyRegisteredException
from app.identity.domain.value_objects import AuthProvider
from tests.fakes.fake_ports import FakeClock, FakePasswordHasher
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


async def test_register_creates_unverified_local_user_and_records_event() -> None:
    uow = FakeUnitOfWork()
    use_case = RegisterUserUseCase(uow, FakePasswordHasher(), FakeClock())

    user = await use_case.execute(
        RegisterUserCommand(email="owner@acme.com", password="s3cret-pw", display_name="Ada Owner")
    )

    assert user.auth_provider == AuthProvider.LOCAL
    assert user.is_email_verified is False
    assert user.password_hash == "hashed:s3cret-pw"
    stored = await uow.users.get_by_email("owner@acme.com")
    assert stored is not None
    assert stored.id == user.id


async def test_register_with_duplicate_email_raises() -> None:
    uow = FakeUnitOfWork()
    use_case = RegisterUserUseCase(uow, FakePasswordHasher(), FakeClock())
    await use_case.execute(
        RegisterUserCommand(email="owner@acme.com", password="s3cret-pw", display_name="Ada Owner")
    )

    with pytest.raises(EmailAlreadyRegisteredException):
        await use_case.execute(
            RegisterUserCommand(email="owner@acme.com", password="another-pw", display_name="Someone Else")
        )
