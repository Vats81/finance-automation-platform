import uuid
from dataclasses import dataclass

from app.business.application.ports import BusinessUnitOfWork
from app.business.domain.exceptions import BusinessNotFoundException, NoStripeCustomerException
from app.config.settings import Settings
from app.shared.application.ports import IPaymentGateway


@dataclass(frozen=True)
class StartBillingPortalSessionCommand:
    business_id: uuid.UUID


class StartBillingPortalSessionUseCase:
    def __init__(self, uow: BusinessUnitOfWork, payment_gateway: IPaymentGateway, settings: Settings) -> None:
        self._uow = uow
        self._payment_gateway = payment_gateway
        self._settings = settings

    async def execute(self, command: StartBillingPortalSessionCommand) -> str:
        business = await self._uow.businesses.get_by_id(command.business_id)
        if business is None:
            raise BusinessNotFoundException(f"Business {command.business_id} not found")
        if business.stripe_customer_id is None:
            raise NoStripeCustomerException("No billing history yet — nothing to manage")

        return await self._payment_gateway.create_billing_portal_session(
            customer_id=business.stripe_customer_id,
            return_url=f"{self._settings.frontend_base_url}/app/settings",
        )
