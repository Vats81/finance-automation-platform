import uuid

from app.business.application.commands.handle_stripe_webhook import (
    HandleStripeWebhookCommand,
    HandleStripeWebhookUseCase,
)
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.application.queries.get_business import GetBusinessQuery, GetBusinessUseCase
from app.business.domain.value_objects import BusinessPlan
from app.config.settings import Settings
from app.shared.application.ports import StripeEvent
from tests.fakes.fake_ports import FakePaymentGateway
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

_SETTINGS = Settings(
    STRIPE_SECRET_KEY="sk_test_dummy",
    STRIPE_PRICE_ID_STARTER="price_starter",
    STRIPE_PRICE_ID_PRO="price_pro",
)


async def test_checkout_completed_attaches_customer_subscription_and_plan() -> None:
    uow = FakeUnitOfWork()
    gateway = FakePaymentGateway()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Acme")
    )
    gateway.next_event = StripeEvent(
        type="checkout.session.completed",
        data={
            "client_reference_id": f"{business.id}:starter",
            "customer": "cus_123",
            "subscription": "sub_123",
        },
    )

    await HandleStripeWebhookUseCase(uow, gateway, _SETTINGS).execute(
        HandleStripeWebhookCommand(payload=b"{}", signature="sig")
    )

    refetched = await GetBusinessUseCase(uow).execute(GetBusinessQuery(business_id=business.id))
    assert refetched.stripe_customer_id == "cus_123"
    assert refetched.stripe_subscription_id == "sub_123"
    assert refetched.plan == BusinessPlan.STARTER


async def test_subscription_updated_resyncs_plan_from_current_price() -> None:
    uow = FakeUnitOfWork()
    gateway = FakePaymentGateway()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Acme")
    )
    business.activate_subscription(subscription_id="sub_123", plan=BusinessPlan.STARTER)
    await uow.businesses.update(business)
    await uow.commit()

    gateway.next_event = StripeEvent(
        type="customer.subscription.updated",
        data={"id": "sub_123", "items": {"data": [{"price": {"id": "price_pro"}}]}},
    )

    await HandleStripeWebhookUseCase(uow, gateway, _SETTINGS).execute(
        HandleStripeWebhookCommand(payload=b"{}", signature="sig")
    )

    refetched = await GetBusinessUseCase(uow).execute(GetBusinessQuery(business_id=business.id))
    assert refetched.plan == BusinessPlan.PRO


async def test_subscription_deleted_resets_to_free_and_clears_subscription_id() -> None:
    uow = FakeUnitOfWork()
    gateway = FakePaymentGateway()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Acme")
    )
    business.activate_subscription(subscription_id="sub_123", plan=BusinessPlan.PRO)
    await uow.businesses.update(business)
    await uow.commit()

    gateway.next_event = StripeEvent(type="customer.subscription.deleted", data={"id": "sub_123"})

    await HandleStripeWebhookUseCase(uow, gateway, _SETTINGS).execute(
        HandleStripeWebhookCommand(payload=b"{}", signature="sig")
    )

    refetched = await GetBusinessUseCase(uow).execute(GetBusinessQuery(business_id=business.id))
    assert refetched.plan == BusinessPlan.FREE
    assert refetched.stripe_subscription_id is None


async def test_unrecognized_event_type_is_a_no_op() -> None:
    uow = FakeUnitOfWork()
    gateway = FakePaymentGateway()
    gateway.next_event = StripeEvent(type="invoice.payment_failed", data={})

    # Must not raise.
    await HandleStripeWebhookUseCase(uow, gateway, _SETTINGS).execute(
        HandleStripeWebhookCommand(payload=b"{}", signature="sig")
    )
