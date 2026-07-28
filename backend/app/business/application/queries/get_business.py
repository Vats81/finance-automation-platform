import uuid
from dataclasses import dataclass

from app.business.application.ports import BusinessUnitOfWork
from app.business.domain.entities import Business
from app.business.domain.exceptions import BusinessNotFoundException


@dataclass(frozen=True)
class GetBusinessQuery:
    business_id: uuid.UUID


class GetBusinessUseCase:
    def __init__(self, uow: BusinessUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: GetBusinessQuery) -> Business:
        business = await self._uow.businesses.get_by_id(query.business_id)
        if business is None:
            raise BusinessNotFoundException(f"Business {query.business_id} not found")
        return business
