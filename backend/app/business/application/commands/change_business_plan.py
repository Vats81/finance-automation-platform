import uuid
from dataclasses import dataclass

from app.business.application.ports import BusinessUnitOfWork
from app.business.domain.entities import Business
from app.business.domain.exceptions import BusinessNotFoundException
from app.business.domain.value_objects import BusinessPlan


@dataclass(frozen=True)
class ChangeBusinessPlanCommand:
    business_id: uuid.UUID
    plan: BusinessPlan


class ChangeBusinessPlanUseCase:
    def __init__(self, uow: BusinessUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: ChangeBusinessPlanCommand) -> Business:
        business = await self._uow.businesses.get_by_id(command.business_id)
        if business is None:
            raise BusinessNotFoundException(f"Business {command.business_id} not found")

        business.change_plan(plan=command.plan)
        await self._uow.businesses.update(business)
        await self._uow.commit()
        return business
