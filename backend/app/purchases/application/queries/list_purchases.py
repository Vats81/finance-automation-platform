import uuid
from dataclasses import dataclass

from app.purchases.application.ports import PurchasesUnitOfWork
from app.purchases.domain.entities import Purchase
from app.shared.application.pagination import Page, PageRequest


@dataclass(frozen=True)
class ListPurchasesQuery:
    business_id: uuid.UUID
    page: PageRequest


class ListPurchasesUseCase:
    def __init__(self, uow: PurchasesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListPurchasesQuery) -> Page[Purchase]:
        purchases, total = await self._uow.purchases.list_for_business(
            query.business_id, offset=query.page.offset, limit=query.page.limit
        )
        return Page(items=purchases, total=total, offset=query.page.offset, limit=query.page.limit)
