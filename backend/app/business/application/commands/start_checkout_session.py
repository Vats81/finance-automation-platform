import uuid
from dataclasses import dataclass

from app.business.application.ports import BusinessUnitOfWork
from app.business.domain.exceptions import (
    ActiveSubscriptionExistsException,
    BusinessNotFoundException,
    DirectPlanChangeNotAllowedException,
)
from app.business.domain.value_objects import BusinessPlan
from app.config.settings import Settings
from app.shared.application.ports import IPaymentGateway


@dataclass(frozen=True)
class StartCheckoutSessionCommand:
    business_id: uuid.UUID
    plan: BusinessPlan
    actor_email: str


class StartCheckoutSessionUseCase:
    """Starts a real (Stripe-hosted) checkout for a paid plan. Rejects FREE
    (nothing to check out for — reuses DirectPlanChangeNotAllowedException's
    "paid plans only go through checkout" framing, inverted) and rejects a
    business that already has a live subscription (change plans via the
    billing portal instead, not a second checkout).
    """

    def __init__(self, uow: BusinessUnitOfWork, payment_gateway: IPaymentGateway, settings: Settings) -> None:
        self._uow = uow
        self._payment_gateway = payment_gateway
        self._settings = settings

    async def execute(self, command: StartCheckoutSessionCommand) -> str:
        business = await self._uow.businesses.get_by_id(command.business_id)
        if business is None:
            raise BusinessNotFoundException(f"Business {command.business_id} not found")

        if command.plan == BusinessPlan.FREE:
            raise DirectPlanChangeNotAllowedException("Nothing to check out for the Free plan")
        if business.stripe_subscription_id is not None:
            raise ActiveSubscriptionExistsException("Use the billing portal to change your existing plan")

        price_id = {
            BusinessPlan.STARTER: self._settings.stripe_price_id_starter,
            BusinessPlan.PRO: self._settings.stripe_price_id_pro,
        }[command.plan]

        base_url = self._settings.frontend_base_url
        return await self._payment_gateway.create_checkout_session(
            customer_id=business.stripe_customer_id,
            customer_email=command.actor_email,
            price_id=price_id,
            client_reference_id=f"{business.id}:{command.plan.value}",
            success_url=f"{base_url}/app/settings?checkout=success",
            cancel_url=f"{base_url}/app/settings?checkout=cancelled",
        )
