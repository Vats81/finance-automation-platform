import uuid
from dataclasses import dataclass

from app.sales.application.ports import SalesUnitOfWork
from app.sales.domain.entities import Sale
from app.shared.application.pagination import Page, PageRequest


@dataclass(frozen=True)
class ListSalesQuery:
    business_id: uuid.UUID
    page: PageRequest


class ListSalesUseCase:
    def __init__(self, uow: SalesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListSalesQuery) -> Page[Sale]:
        sales, total = await self._uow.sales.list_for_business(
            query.business_id, offset=query.page.offset, limit=query.page.limit
        )
        return Page(items=sales, total=total, offset=query.page.offset, limit=query.page.limit)
