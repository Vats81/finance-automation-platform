import uuid
from dataclasses import dataclass

from app.sales.application.ports import SalesUnitOfWork
from app.sales.domain.entities import Sale
from app.sales.domain.exceptions import SaleNotFoundException


@dataclass(frozen=True)
class GetSaleQuery:
    business_id: uuid.UUID
    sale_id: uuid.UUID


class GetSaleUseCase:
    def __init__(self, uow: SalesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: GetSaleQuery) -> Sale:
        sale = await self._uow.sales.get_by_id_for_business(query.sale_id, query.business_id)
        if sale is None:
            raise SaleNotFoundException(f"Sale {query.sale_id} not found")
        return sale
