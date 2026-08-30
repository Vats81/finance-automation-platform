import uuid

import pytest

from app.business.application.commands.change_business_plan import (
    ChangeBusinessPlanCommand,
    ChangeBusinessPlanUseCase,
)
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.application.queries.get_business import GetBusinessQuery, GetBusinessUseCase
from app.business.domain.exceptions import (
    ActiveSubscriptionExistsException,
    DirectPlanChangeNotAllowedException,
)
from app.business.domain.value_objects import BusinessPlan
from app.config.settings import Settings
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

_NO_STRIPE = Settings()
_STRIPE_CONFIGURED = Settings(STRIPE_SECRET_KEY="sk_test_dummy")


async def test_change_plan_persists_and_is_reflected_on_refetch() -> None:
    uow = FakeUnitOfWork()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Acme")
    )

    await ChangeBusinessPlanUseCase(uow, _NO_STRIPE).execute(
        ChangeBusinessPlanCommand(business_id=business.id, plan=BusinessPlan.STARTER)
    )

    refetched = await GetBusinessUseCase(uow).execute(GetBusinessQuery(business_id=business.id))
    assert refetched.plan == BusinessPlan.STARTER


async def test_stripe_configured_blocks_direct_flip_to_paid_plan() -> None:
    uow = FakeUnitOfWork()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Acme")
    )

    with pytest.raises(DirectPlanChangeNotAllowedException):
        await ChangeBusinessPlanUseCase(uow, _STRIPE_CONFIGURED).execute(
            ChangeBusinessPlanCommand(business_id=business.id, plan=BusinessPlan.PRO)
        )


async def test_stripe_configured_still_allows_direct_flip_to_free_with_no_subscription() -> None:
    uow = FakeUnitOfWork()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Acme")
    )

    await ChangeBusinessPlanUseCase(uow, _STRIPE_CONFIGURED).execute(
        ChangeBusinessPlanCommand(business_id=business.id, plan=BusinessPlan.FREE)
    )

    refetched = await GetBusinessUseCase(uow).execute(GetBusinessQuery(business_id=business.id))
    assert refetched.plan == BusinessPlan.FREE


async def test_stripe_configured_blocks_flip_to_free_while_subscription_active() -> None:
    uow = FakeUnitOfWork()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Acme")
    )
    business.activate_subscription(subscription_id="sub_123", plan=BusinessPlan.PRO)
    await uow.businesses.update(business)
    await uow.commit()

    with pytest.raises(ActiveSubscriptionExistsException):
        await ChangeBusinessPlanUseCase(uow, _STRIPE_CONFIGURED).execute(
            ChangeBusinessPlanCommand(business_id=business.id, plan=BusinessPlan.FREE)
        )
