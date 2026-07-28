import uuid
from dataclasses import dataclass

from app.purchase_orders.application.ports import PurchaseOrdersUnitOfWork
from app.purchase_orders.domain.entities import PurchaseOrder
from app.purchase_orders.domain.exceptions import PurchaseOrderNotFoundException


@dataclass(frozen=True)
class GetPurchaseOrderQuery:
    po_id: uuid.UUID


class GetPurchaseOrderUseCase:
    def __init__(self, uow: PurchaseOrdersUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: GetPurchaseOrderQuery) -> PurchaseOrder:
        po = await self._uow.purchase_orders.get_by_id(query.po_id)
        if po is None:
            raise PurchaseOrderNotFoundException(f"PurchaseOrder {query.po_id} not found")
        return po
