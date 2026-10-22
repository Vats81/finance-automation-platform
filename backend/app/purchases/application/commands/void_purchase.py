import uuid
from dataclasses import dataclass

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.purchases.application.stock import remove_added_stock
from app.purchases.domain.entities import Purchase
from app.purchases.domain.exceptions import PurchaseAlreadyVoidException, PurchaseNotFoundException
from app.purchases.domain.value_objects import PurchaseStatus


@dataclass(frozen=True)
class VoidPurchaseCommand:
    business_id: uuid.UUID
    purchase_id: uuid.UUID


class VoidPurchaseUseCase:
    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: VoidPurchaseCommand) -> Purchase:
        purchase = await self._uow.purchases.get_by_id_for_business(command.purchase_id, command.business_id)
        if purchase is None:
            raise PurchaseNotFoundException(f"Purchase {command.purchase_id} not found")

        if purchase.status == PurchaseStatus.VOID:
            raise PurchaseAlreadyVoidException(f"Purchase {purchase.id} is already void")
        # Stock first: if it can't be taken back, the purchase must stay exactly as it was.
        if purchase.stock_added:
            await remove_added_stock(self._uow, purchase)
        purchase.void()
        await self._uow.purchases.update(purchase)
        await self._uow.commit()
        return purchase
