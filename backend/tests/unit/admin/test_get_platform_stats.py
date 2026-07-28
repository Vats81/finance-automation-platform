from datetime import datetime, timedelta, timezone

from app.admin.application.queries.get_platform_stats import GetPlatformStatsUseCase
from app.business.application.commands.change_business_plan import (
    ChangeBusinessPlanCommand,
    ChangeBusinessPlanUseCase,
)
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.domain.value_objects import BusinessPlan
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


async def test_platform_stats_tally_plan_breakdown_and_verification_split() -> None:
    uow = FakeUnitOfWork()

    free_owner = seed_user(uow, "free@example.com", verified=True)
    await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=free_owner.id, name="Free Co")
    )

    pro_owner = seed_user(uow, "pro@example.com", verified=False)
    pro_business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=pro_owner.id, name="Pro Co")
    )
    await ChangeBusinessPlanUseCase(uow).execute(
        ChangeBusinessPlanCommand(business_id=pro_business.id, plan=BusinessPlan.PRO)
    )

    stats = await GetPlatformStatsUseCase(uow).execute()

    assert stats.total_businesses == 2
    assert stats.total_users == 2
    assert stats.businesses_by_plan == {"free": 1, "pro": 1}
    assert stats.verified_users == 1
    assert stats.unverified_users == 1


async def test_platform_stats_empty_platform() -> None:
    uow = FakeUnitOfWork()

    stats = await GetPlatformStatsUseCase(uow).execute()

    assert stats.total_businesses == 0
    assert stats.total_users == 0
    assert stats.businesses_by_plan == {}
    assert stats.verified_users == 0
    assert stats.unverified_users == 0
