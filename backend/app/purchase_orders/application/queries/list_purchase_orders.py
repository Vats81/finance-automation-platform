from dataclasses import dataclass

from app.purchase_orders.application.ports import PurchaseOrdersUnitOfWork
from app.purchase_orders.domain.entities import PurchaseOrder
from app.shared.application.pagination import Page, PageRequest


@dataclass(frozen=True)
class ListPurchaseOrdersQuery:
    page: PageRequest


class ListPurchaseOrdersUseCase:
    def __init__(self, uow: PurchaseOrdersUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListPurchaseOrdersQuery) -> Page[PurchaseOrder]:
        pos, total = await self._uow.purchase_orders.list_all(
            offset=query.page.offset, limit=query.page.limit
        )
        return Page(items=pos, total=total, offset=query.page.offset, limit=query.page.limit)
