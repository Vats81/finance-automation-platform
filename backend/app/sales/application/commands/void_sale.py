import uuid
from dataclasses import dataclass

from app.sales.application.ports import SalesUnitOfWork
from app.sales.domain.entities import Sale
from app.sales.domain.exceptions import SaleNotFoundException


@dataclass(frozen=True)
class VoidSaleCommand:
    business_id: uuid.UUID
    sale_id: uuid.UUID


class VoidSaleUseCase:
    def __init__(self, uow: SalesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: VoidSaleCommand) -> Sale:
        sale = await self._uow.sales.get_by_id_for_business(command.sale_id, command.business_id)
        if sale is None:
            raise SaleNotFoundException(f"Sale {command.sale_id} not found")

        sale.void()
        await self._uow.sales.update(sale)
        await self._uow.commit()
        return sale
