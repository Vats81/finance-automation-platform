from datetime import datetime, timedelta, timezone

from app.admin.application.queries.list_businesses_overview import (
    ListBusinessesOverviewQuery,
    ListBusinessesOverviewUseCase,
)
from app.business.application.commands.change_business_plan import (
    ChangeBusinessPlanCommand,
    ChangeBusinessPlanUseCase,
)
from app.business.application.commands.invite_team_member import (
    InviteTeamMemberCommand,
    InviteTeamMemberUseCase,
)
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.domain.value_objects import BusinessPlan, BusinessRole
from app.config.settings import Settings
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


async def test_list_businesses_overview_resolves_plan_owner_and_member_count() -> None:
    uow = FakeUnitOfWork()
    owner = seed_user(uow, "owner@example.com")
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=owner.id, name="Acme")
    )
    await ChangeBusinessPlanUseCase(uow, Settings()).execute(
        ChangeBusinessPlanCommand(business_id=business.id, plan=BusinessPlan.PRO)
    )
    seed_user(uow, "teammate@example.com")
    await InviteTeamMemberUseCase(uow, FakeEmailSender()).execute(
        InviteTeamMemberCommand(
            business_id=business.id,
            invited_by_user_id=owner.id,
            email="teammate@example.com",
            role=BusinessRole.VIEWER,
        )
    )

    page = await ListBusinessesOverviewUseCase(uow).execute(ListBusinessesOverviewQuery())

    assert page.total == 1
    item = page.items[0]
    assert item.name == "Acme"
    assert item.plan == BusinessPlan.PRO
    assert item.member_count == 2
    assert item.owner_email == "owner@example.com"


async def test_list_businesses_overview_empty_platform() -> None:
    uow = FakeUnitOfWork()

    page = await ListBusinessesOverviewUseCase(uow).execute(ListBusinessesOverviewQuery())

    assert page.total == 0
    assert page.items == []


async def test_list_businesses_overview_respects_pagination() -> None:
    uow = FakeUnitOfWork()
    for i in range(3):
        owner = seed_user(uow, f"owner{i}@example.com")
        await RegisterBusinessUseCase(uow).execute(
            RegisterBusinessCommand(owner_user_id=owner.id, name=f"Business {i}")
        )

    page = await ListBusinessesOverviewUseCase(uow).execute(ListBusinessesOverviewQuery(offset=0, limit=2))

    assert page.total == 3
    assert len(page.items) == 2
    assert page.offset == 0
    assert page.limit == 2
