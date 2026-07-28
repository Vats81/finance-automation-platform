import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.expenses.application.ports import ExpensesUnitOfWork
from app.expenses.domain.entities import Expense
from app.expenses.domain.value_objects import PaymentMethod
from app.shared.domain.value_objects import Money


@dataclass(frozen=True)
class CreateExpenseCommand:
    business_id: uuid.UUID
    expense_date: date
    category: str
    description: str
    amount: Decimal
    payment_method: PaymentMethod
    vendor_id: uuid.UUID | None = None
    tax: Decimal | None = None
    is_recurring: bool = False
    notes: str | None = None


class CreateExpenseUseCase:
    def __init__(self, uow: ExpensesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: CreateExpenseCommand) -> Expense:
        expense = Expense.create(
            business_id=command.business_id,
            expense_date=command.expense_date,
            category=command.category,
            description=command.description,
            amount=Money(amount=command.amount),
            payment_method=command.payment_method,
            vendor_id=command.vendor_id,
            tax=Money(amount=command.tax) if command.tax is not None else None,
            is_recurring=command.is_recurring,
            notes=command.notes,
        )
        self._uow.expenses.add(expense)
        await self._uow.commit()
        return expense
