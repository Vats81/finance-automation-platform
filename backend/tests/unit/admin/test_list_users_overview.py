from datetime import datetime, timedelta, timezone

from app.admin.application.queries.list_users_overview import (
    ListUsersOverviewQuery,
    ListUsersOverviewUseCase,
)
from app.identity.domain.entities import User
from app.identity.domain.value_objects import EmailAddress
from tests.fakes.fake_ports import FakePasswordHasher
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


def seed_user(uow: FakeUnitOfWork, email: str, *, verified: bool = False) -> User:
    hasher = FakePasswordHasher()
    token = "tok"
    user = User.register(
        email=EmailAddress(email),
        display_name="Test User",
        password_hash=hasher.hash("pw"),
        verification_token=token,
        verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    if verified:
        user.verify_email(token=token, now=datetime.now(timezone.utc))
    uow.users.add(user)
    return user


async def test_list_users_overview_returns_correct_fields_and_total() -> None:
    uow = FakeUnitOfWork()
    seed_user(uow, "verified@example.com", verified=True)
    seed_user(uow, "unverified@example.com", verified=False)

    page = await ListUsersOverviewUseCase(uow).execute(ListUsersOverviewQuery())

    assert page.total == 2
    emails = {item.email for item in page.items}
    assert emails == {"verified@example.com", "unverified@example.com"}
    verified_item = next(i for i in page.items if i.email == "verified@example.com")
    assert verified_item.is_email_verified is True
    assert verified_item.is_active is True
