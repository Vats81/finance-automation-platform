import uuid
from dataclasses import dataclass

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.domain.entities import Business
from app.business.domain.exceptions import BusinessNotFoundException


@dataclass(frozen=True)
class SuspendBusinessCommand:
    business_id: uuid.UUID


class SuspendBusinessUseCase:
    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: SuspendBusinessCommand) -> Business:
        business = await self._uow.businesses.get_by_id(command.business_id)
        if business is None:
            raise BusinessNotFoundException(f"Business {command.business_id} not found")

        business.suspend()
        await self._uow.businesses.update(business)
        await self._uow.commit()
        return business
