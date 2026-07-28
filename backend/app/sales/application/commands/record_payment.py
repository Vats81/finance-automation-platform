import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.sales.application.ports import SalesUnitOfWork
from app.sales.domain.entities import Sale
from app.sales.domain.exceptions import SaleNotFoundException
from app.shared.domain.value_objects import Money


@dataclass(frozen=True)
class RecordSalePaymentCommand:
    business_id: uuid.UUID
    sale_id: uuid.UUID
    amount: Decimal


class RecordSalePaymentUseCase:
    def __init__(self, uow: SalesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: RecordSalePaymentCommand) -> Sale:
        sale = await self._uow.sales.get_by_id_for_business(command.sale_id, command.business_id)
        if sale is None:
            raise SaleNotFoundException(f"Sale {command.sale_id} not found")

        sale.record_payment(Money(amount=command.amount))
        await self._uow.sales.update(sale)
        await self._uow.commit()
        return sale
