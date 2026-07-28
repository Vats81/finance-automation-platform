from dataclasses import dataclass

from app.invoices.application.ports import InvoicesUnitOfWork
from app.invoices.domain.entities import Invoice
from app.shared.application.pagination import Page, PageRequest


@dataclass(frozen=True)
class ListInvoicesQuery:
    page: PageRequest


class ListInvoicesUseCase:
    def __init__(self, uow: InvoicesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListInvoicesQuery) -> Page[Invoice]:
        invoices, total = await self._uow.invoices.list_all(offset=query.page.offset, limit=query.page.limit)
        return Page(items=invoices, total=total, offset=query.page.offset, limit=query.page.limit)
