from dataclasses import dataclass

from app.payments.application.ports import PaymentsUnitOfWork
from app.payments.domain.entities import Payment
from app.shared.application.pagination import Page, PageRequest


@dataclass(frozen=True)
class ListPaymentsQuery:
    page: PageRequest


class ListPaymentsUseCase:
    def __init__(self, uow: PaymentsUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListPaymentsQuery) -> Page[Payment]:
        payments, total = await self._uow.payments.list_all(offset=query.page.offset, limit=query.page.limit)
        return Page(items=payments, total=total, offset=query.page.offset, limit=query.page.limit)
