import uuid
from dataclasses import dataclass

from app.business.application.ports import BusinessUnitOfWork
from app.business.domain.entities import Business
from app.business.domain.exceptions import BusinessNotFoundException


@dataclass(frozen=True)
class CompleteOnboardingCommand:
    business_id: uuid.UUID
    business_type: str | None = None
    industry: str | None = None
    country: str | None = None
    currency: str | None = None
    financial_year_start_month: int | None = None
    gst_registered: bool | None = None
    business_size: str | None = None
    number_of_branches: int | None = None
    whatsapp_number: str | None = None
    contact_email: str | None = None


class CompleteOnboardingUseCase:
    def __init__(self, uow: BusinessUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: CompleteOnboardingCommand) -> Business:
        business = await self._uow.businesses.get_by_id(command.business_id)
        if business is None:
            raise BusinessNotFoundException(f"Business {command.business_id} not found")

        business.complete_onboarding(
            business_type=command.business_type,
            industry=command.industry,
            country=command.country,
            currency=command.currency,
            financial_year_start_month=command.financial_year_start_month,
            gst_registered=command.gst_registered,
            business_size=command.business_size,
            number_of_branches=command.number_of_branches,
            whatsapp_number=command.whatsapp_number,
            contact_email=command.contact_email,
        )
        await self._uow.businesses.update(business)
        await self._uow.commit()
        return business
