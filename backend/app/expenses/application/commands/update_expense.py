import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.expenses.application.ports import ExpensesUnitOfWork
from app.expenses.domain.entities import Expense
from app.expenses.domain.exceptions import ExpenseNotFoundException
from app.expenses.domain.value_objects import PaymentMethod
from app.shared.domain.value_objects import Money


@dataclass(frozen=True)
class UpdateExpenseCommand:
    business_id: uuid.UUID
    expense_id: uuid.UUID
    category: str | None = None
    description: str | None = None
    amount: Decimal | None = None
    tax: Decimal | None = None
    payment_method: PaymentMethod | None = None
    is_recurring: bool | None = None
    notes: str | None = None


class UpdateExpenseUseCase:
    def __init__(self, uow: ExpensesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: UpdateExpenseCommand) -> Expense:
        expense = await self._uow.expenses.get_by_id_for_business(command.expense_id, command.business_id)
        if expense is None:
            raise ExpenseNotFoundException(f"Expense {command.expense_id} not found")

        expense.update_details(
            category=command.category,
            description=command.description,
            amount=Money(amount=command.amount) if command.amount is not None else None,
            tax=Money(amount=command.tax) if command.tax is not None else None,
            payment_method=command.payment_method,
            is_recurring=command.is_recurring,
            notes=command.notes,
        )
        await self._uow.expenses.update(expense)
        await self._uow.commit()
        return expense
