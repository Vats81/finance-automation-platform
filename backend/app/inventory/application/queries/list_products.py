import uuid
from dataclasses import dataclass

from app.inventory.application.ports import InventoryUnitOfWork
from app.inventory.domain.entities import Product
from app.shared.application.pagination import Page, PageRequest


@dataclass(frozen=True)
class ListProductsQuery:
    business_id: uuid.UUID
    page: PageRequest


class ListProductsUseCase:
    def __init__(self, uow: InventoryUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListProductsQuery) -> Page[Product]:
        products, total = await self._uow.products.list_for_business(
            query.business_id, offset=query.page.offset, limit=query.page.limit
        )
        return Page(items=products, total=total, offset=query.page.offset, limit=query.page.limit)
