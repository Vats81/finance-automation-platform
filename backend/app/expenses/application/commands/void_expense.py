import uuid
from dataclasses import dataclass

from app.expenses.application.ports import ExpensesUnitOfWork
from app.expenses.domain.entities import Expense
from app.expenses.domain.exceptions import ExpenseNotFoundException


@dataclass(frozen=True)
class VoidExpenseCommand:
    business_id: uuid.UUID
    expense_id: uuid.UUID


class VoidExpenseUseCase:
    def __init__(self, uow: ExpensesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: VoidExpenseCommand) -> Expense:
        expense = await self._uow.expenses.get_by_id_for_business(command.expense_id, command.business_id)
        if expense is None:
            raise ExpenseNotFoundException(f"Expense {command.expense_id} not found")

        expense.void()
        await self._uow.expenses.update(expense)
        await self._uow.commit()
        return expense
