import uuid
from dataclasses import dataclass

from app.purchases.application.ports import PurchasesUnitOfWork
from app.purchases.domain.entities import Purchase
from app.purchases.domain.exceptions import PurchaseNotFoundException


@dataclass(frozen=True)
class VoidPurchaseCommand:
    business_id: uuid.UUID
    purchase_id: uuid.UUID


class VoidPurchaseUseCase:
    def __init__(self, uow: PurchasesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: VoidPurchaseCommand) -> Purchase:
        purchase = await self._uow.purchases.get_by_id_for_business(command.purchase_id, command.business_id)
        if purchase is None:
            raise PurchaseNotFoundException(f"Purchase {command.purchase_id} not found")

        purchase.void()
        await self._uow.purchases.update(purchase)
        await self._uow.commit()
        return purchase
