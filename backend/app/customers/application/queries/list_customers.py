import uuid
from dataclasses import dataclass

from app.customers.application.ports import CustomersUnitOfWork
from app.customers.domain.entities import Customer
from app.shared.application.pagination import Page, PageRequest


@dataclass(frozen=True)
class ListCustomersQuery:
    business_id: uuid.UUID
    page: PageRequest


class ListCustomersUseCase:
    def __init__(self, uow: CustomersUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListCustomersQuery) -> Page[Customer]:
        customers, total = await self._uow.customers.list_for_business(
            query.business_id, offset=query.page.offset, limit=query.page.limit
        )
        return Page(items=customers, total=total, offset=query.page.offset, limit=query.page.limit)
