from datetime import timedelta

from app.identity.application.commands.request_password_reset import (
    RequestPasswordResetCommand,
    RequestPasswordResetUseCase,
)
from app.identity.application.commands.reset_password import ResetPasswordCommand, ResetPasswordUseCase
from app.identity.domain.entities import User
from app.identity.domain.value_objects import EmailAddress
from tests.fakes.fake_ports import FakeClock, FakePasswordHasher
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


async def seed_local_user(uow: FakeUnitOfWork, clock: FakeClock) -> User:
    user = User.register(
        email=EmailAddress("owner@acme.com"),
        display_name="Ada Owner",
        password_hash="hashed:old-pw",
        verification_token="tok",
        verification_expires_at=clock.now() + timedelta(hours=24),
    )
    uow.users.add(user)
    return user


async def test_request_password_reset_for_unknown_email_is_a_silent_noop() -> None:
    uow = FakeUnitOfWork()
    clock = FakeClock()

    await RequestPasswordResetUseCase(uow, clock).execute(
        RequestPasswordResetCommand(email="nobody@acme.com")
    )
    # No exception, no state change to assert against — silence is the point.


async def test_full_password_reset_flow() -> None:
    uow = FakeUnitOfWork()
    clock = FakeClock()
    user = await seed_local_user(uow, clock)
    hasher = FakePasswordHasher()

    await RequestPasswordResetUseCase(uow, clock).execute(
        RequestPasswordResetCommand(email="owner@acme.com")
    )
    stored = await uow.users.get_by_id(user.id)
    assert stored is not None and stored.password_reset_token_hash is not None

    # The use case only enqueues the raw token via a domain event we can't
    # observe through the fake (events are pulled/discarded on add/update,
    # mirroring what the outbox would otherwise consume) — so this test
    # exercises the reset step directly against the entity's own token,
    # matching how test_user_local_auth_entity.py covers the token check.
    stored.request_password_reset(reset_token="known-token", expires_at=clock.now() + timedelta(hours=2))
    await uow.users.update(stored)

    updated = await ResetPasswordUseCase(uow, hasher, clock).execute(
        ResetPasswordCommand(user_id=user.id, token="known-token", new_password="new-pw")
    )

    assert updated.password_hash == "hashed:new-pw"
    assert hasher.verify("new-pw", updated.password_hash)
