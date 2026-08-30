import uuid
from dataclasses import dataclass

from app.business.application.ports import BusinessUnitOfWork
from app.business.domain.entities import Business
from app.business.domain.exceptions import (
    ActiveSubscriptionExistsException,
    BusinessNotFoundException,
    DirectPlanChangeNotAllowedException,
)
from app.business.domain.value_objects import BusinessPlan
from app.config.settings import Settings


@dataclass(frozen=True)
class ChangeBusinessPlanCommand:
    business_id: uuid.UUID
    plan: BusinessPlan


class ChangeBusinessPlanUseCase:
    """Direct, unpaid plan flip — the only mechanism that exists at all
    until Stripe is configured. Once settings.stripe_configured is true,
    this tightens: paid plans must go through a real checkout
    (StartCheckoutSessionUseCase) instead, and a business can't flip back
    to FREE while a live Stripe subscription would keep charging it (must
    cancel via the billing portal, which syncs back through the webhook).
    When Stripe isn't configured, behavior is unchanged from before this
    tightening existed — no regression for any deployment that never turns
    billing on.
    """

    def __init__(self, uow: BusinessUnitOfWork, settings: Settings) -> None:
        self._uow = uow
        self._settings = settings

    async def execute(self, command: ChangeBusinessPlanCommand) -> Business:
        business = await self._uow.businesses.get_by_id(command.business_id)
        if business is None:
            raise BusinessNotFoundException(f"Business {command.business_id} not found")

        if self._settings.stripe_configured:
            if command.plan != BusinessPlan.FREE:
                raise DirectPlanChangeNotAllowedException(
                    "Paid plans must be purchased through checkout, not set directly"
                )
            if business.stripe_subscription_id is not None:
                raise ActiveSubscriptionExistsException(
                    "Cancel your subscription in the billing portal first"
                )

        business.change_plan(plan=command.plan)
        await self._uow.businesses.update(business)
        await self._uow.commit()
        return business
