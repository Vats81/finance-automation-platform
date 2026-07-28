import uuid

from app.business.application.commands.change_business_plan import (
    ChangeBusinessPlanCommand,
    ChangeBusinessPlanUseCase,
)
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.application.queries.get_business import GetBusinessQuery, GetBusinessUseCase
from app.business.domain.value_objects import BusinessPlan
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


async def test_change_plan_persists_and_is_reflected_on_refetch() -> None:
    uow = FakeUnitOfWork()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Acme")
    )

    await ChangeBusinessPlanUseCase(uow).execute(
        ChangeBusinessPlanCommand(business_id=business.id, plan=BusinessPlan.STARTER)
    )

    refetched = await GetBusinessUseCase(uow).execute(GetBusinessQuery(business_id=business.id))
    assert refetched.plan == BusinessPlan.STARTER
