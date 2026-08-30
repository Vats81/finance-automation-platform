import uuid

import pytest

from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.application.commands.start_checkout_session import (
    StartCheckoutSessionCommand,
    StartCheckoutSessionUseCase,
)
from app.business.domain.exceptions import (
    ActiveSubscriptionExistsException,
    DirectPlanChangeNotAllowedException,
)
from app.business.domain.value_objects import BusinessPlan
from app.config.settings import Settings
from tests.fakes.fake_ports import FakePaymentGateway
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

_SETTINGS = Settings(
    STRIPE_SECRET_KEY="sk_test_dummy",
    STRIPE_PRICE_ID_STARTER="price_starter",
    STRIPE_PRICE_ID_PRO="price_pro",
)


async def test_start_checkout_session_returns_url_and_encodes_business_and_plan() -> None:
    uow = FakeUnitOfWork()
    gateway = FakePaymentGateway()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Acme")
    )

    url = await StartCheckoutSessionUseCase(uow, gateway, _SETTINGS).execute(
        StartCheckoutSessionCommand(
            business_id=business.id, plan=BusinessPlan.STARTER, actor_email="owner@example.com"
        )
    )

    assert url == f"https://checkout.stripe.com/fake/{business.id}:starter"
    assert len(gateway.checkout_calls) == 1
    call = gateway.checkout_calls[0]
    assert call["price_id"] == "price_starter"
    assert call["client_reference_id"] == f"{business.id}:starter"
    assert call["customer_email"] == "owner@example.com"
    assert call["customer_id"] is None


async def test_start_checkout_session_rejects_free_plan() -> None:
    uow = FakeUnitOfWork()
    gateway = FakePaymentGateway()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Acme")
    )

    with pytest.raises(DirectPlanChangeNotAllowedException):
        await StartCheckoutSessionUseCase(uow, gateway, _SETTINGS).execute(
            StartCheckoutSessionCommand(
                business_id=business.id, plan=BusinessPlan.FREE, actor_email="owner@example.com"
            )
        )


async def test_start_checkout_session_rejects_business_with_existing_subscription() -> None:
    uow = FakeUnitOfWork()
    gateway = FakePaymentGateway()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Acme")
    )
    business.activate_subscription(subscription_id="sub_123", plan=BusinessPlan.STARTER)
    await uow.businesses.update(business)
    await uow.commit()

    with pytest.raises(ActiveSubscriptionExistsException):
        await StartCheckoutSessionUseCase(uow, gateway, _SETTINGS).execute(
            StartCheckoutSessionCommand(
                business_id=business.id, plan=BusinessPlan.PRO, actor_email="owner@example.com"
            )
        )
