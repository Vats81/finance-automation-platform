import uuid
from dataclasses import dataclass

from app.expenses.application.ports import ExpensesUnitOfWork
from app.expenses.domain.entities import Expense
from app.expenses.domain.exceptions import ExpenseNotFoundException


@dataclass(frozen=True)
class GetExpenseQuery:
    business_id: uuid.UUID
    expense_id: uuid.UUID


class GetExpenseUseCase:
    def __init__(self, uow: ExpensesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: GetExpenseQuery) -> Expense:
        expense = await self._uow.expenses.get_by_id_for_business(query.expense_id, query.business_id)
        if expense is None:
            raise ExpenseNotFoundException(f"Expense {query.expense_id} not found")
        return expense
