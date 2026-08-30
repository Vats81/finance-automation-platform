import uuid

import pytest

from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.application.commands.start_billing_portal_session import (
    StartBillingPortalSessionCommand,
    StartBillingPortalSessionUseCase,
)
from app.business.domain.exceptions import NoStripeCustomerException
from app.config.settings import Settings
from tests.fakes.fake_ports import FakePaymentGateway
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

_SETTINGS = Settings(STRIPE_SECRET_KEY="sk_test_dummy")


async def test_start_billing_portal_session_returns_url_for_existing_customer() -> None:
    uow = FakeUnitOfWork()
    gateway = FakePaymentGateway()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Acme")
    )
    business.attach_stripe_customer(customer_id="cus_123")
    await uow.businesses.update(business)
    await uow.commit()

    url = await StartBillingPortalSessionUseCase(uow, gateway, _SETTINGS).execute(
        StartBillingPortalSessionCommand(business_id=business.id)
    )

    assert url == "https://billing.stripe.com/fake/cus_123"
    expected_return_url = f"{_SETTINGS.frontend_base_url}/app/settings"
    assert gateway.portal_calls == [{"customer_id": "cus_123", "return_url": expected_return_url}]


async def test_start_billing_portal_session_rejects_business_with_no_customer_yet() -> None:
    uow = FakeUnitOfWork()
    gateway = FakePaymentGateway()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Acme")
    )

    with pytest.raises(NoStripeCustomerException):
        await StartBillingPortalSessionUseCase(uow, gateway, _SETTINGS).execute(
            StartBillingPortalSessionCommand(business_id=business.id)
        )
