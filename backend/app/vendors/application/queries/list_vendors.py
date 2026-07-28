from dataclasses import dataclass

from app.shared.application.pagination import Page, PageRequest
from app.vendors.application.ports import VendorsUnitOfWork
from app.vendors.domain.entities import Vendor


@dataclass(frozen=True)
class ListVendorsQuery:
    page: PageRequest


class ListVendorsUseCase:
    def __init__(self, uow: VendorsUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListVendorsQuery) -> Page[Vendor]:
        vendors, total = await self._uow.vendors.list_all(offset=query.page.offset, limit=query.page.limit)
        return Page(items=vendors, total=total, offset=query.page.offset, limit=query.page.limit)
