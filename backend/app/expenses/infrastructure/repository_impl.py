import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.expenses.domain.entities import Expense
from app.expenses.domain.exceptions import ExpenseNotFoundException
from app.expenses.domain.repository import IExpenseRepository
from app.expenses.infrastructure.mappers import (
    apply_domain_to_existing_model,
    domain_to_model,
    model_to_domain,
)
from app.expenses.infrastructure.models import ExpenseModel
from app.shared.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemyExpenseRepository(IExpenseRepository):
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> AsyncSession:
        return self._uow.session

    async def get_by_id_for_business(self, expense_id: uuid.UUID, business_id: uuid.UUID) -> Expense | None:
        stmt = select(ExpenseModel).where(
            ExpenseModel.id == expense_id, ExpenseModel.business_id == business_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model_to_domain(model) if model else None

    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Expense], int]:
        total = (
            await self._session.execute(
                select(func.count()).select_from(ExpenseModel).where(ExpenseModel.business_id == business_id)
            )
        ).scalar_one()
        stmt = (
            select(ExpenseModel)
            .where(ExpenseModel.business_id == business_id)
            .order_by(ExpenseModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        expenses = [model_to_domain(m) for m in result.scalars().all()]
        return expenses, total

    def add(self, expense: Expense) -> None:
        self._session.add(domain_to_model(expense))
        self._uow.collect_events(expense)

    async def update(self, expense: Expense) -> None:
        model = await self._session.get(ExpenseModel, expense.id)
        if model is None:
            raise ExpenseNotFoundException(f"Expense {expense.id} not found")
        apply_domain_to_existing_model(expense, model)
        self._uow.collect_events(expense)
