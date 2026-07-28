import uuid
from dataclasses import dataclass

from app.expenses.application.ports import ExpensesUnitOfWork
from app.expenses.domain.entities import Expense
from app.shared.application.pagination import Page, PageRequest


@dataclass(frozen=True)
class ListExpensesQuery:
    business_id: uuid.UUID
    page: PageRequest


class ListExpensesUseCase:
    def __init__(self, uow: ExpensesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListExpensesQuery) -> Page[Expense]:
        expenses, total = await self._uow.expenses.list_for_business(
            query.business_id, offset=query.page.offset, limit=query.page.limit
        )
        return Page(items=expenses, total=total, offset=query.page.offset, limit=query.page.limit)
