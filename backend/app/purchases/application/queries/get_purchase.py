import uuid
from dataclasses import dataclass

from app.purchases.application.ports import PurchasesUnitOfWork
from app.purchases.domain.entities import Purchase
from app.purchases.domain.exceptions import PurchaseNotFoundException


@dataclass(frozen=True)
class GetPurchaseQuery:
    business_id: uuid.UUID
    purchase_id: uuid.UUID


class GetPurchaseUseCase:
    def __init__(self, uow: PurchasesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: GetPurchaseQuery) -> Purchase:
        purchase = await self._uow.purchases.get_by_id_for_business(query.purchase_id, query.business_id)
        if purchase is None:
            raise PurchaseNotFoundException(f"Purchase {query.purchase_id} not found")
        return purchase
