import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.personal_finance.application.ports import BudgetRecord, IncomeRecord, IPersonalFinanceRepository
from app.personal_finance.infrastructure.models import BudgetModel, IncomeModel
from app.shared.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


_TWO_PLACES = Decimal("0.01")


def _money(cents: int) -> Decimal:
    return (Decimal(cents) / 100).quantize(_TWO_PLACES)


def _cents(amount: Decimal) -> int:
    return int((amount * 100).to_integral_value())


def _income(m: IncomeModel) -> IncomeRecord:
    return IncomeRecord(
        id=m.id,
        business_id=m.business_id,
        income_date=m.income_date,
        source=m.source,
        category=m.category,
        amount=_money(m.amount_cents),
        notes=m.notes,
        status=m.status,
        created_at=m.created_at,
    )


def _budget(m: BudgetModel) -> BudgetRecord:
    return BudgetRecord(
        id=m.id,
        business_id=m.business_id,
        category=m.category,
        monthly_limit=_money(m.monthly_limit_cents),
        created_at=m.created_at,
    )


class SqlAlchemyPersonalFinanceRepository(IPersonalFinanceRepository):
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> AsyncSession:
        return self._uow.session

    async def add_income(
        self,
        *,
        business_id: uuid.UUID,
        income_date: date,
        source: str,
        category: str,
        amount: Decimal,
        notes: str | None,
    ) -> IncomeRecord:
        model = IncomeModel(
            id=uuid.uuid4(),
            business_id=business_id,
            income_date=income_date,
            source=source,
            category=category,
            amount_cents=_cents(amount),
            notes=notes,
            status="recorded",
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _income(model)

    async def _income_row(self, business_id: uuid.UUID, income_id: uuid.UUID) -> IncomeModel | None:
        result = await self._session.execute(
            select(IncomeModel).where(IncomeModel.id == income_id, IncomeModel.business_id == business_id)
        )
        return result.scalar_one_or_none()

    async def get_income(self, business_id: uuid.UUID, income_id: uuid.UUID) -> IncomeRecord | None:
        row = await self._income_row(business_id, income_id)
        return _income(row) if row else None

    async def list_incomes(
        self, business_id: uuid.UUID, *, offset: int, limit: int
    ) -> tuple[list[IncomeRecord], int]:
        total = (
            await self._session.execute(
                select(func.count()).select_from(IncomeModel).where(IncomeModel.business_id == business_id)
            )
        ).scalar_one()
        result = await self._session.execute(
            select(IncomeModel)
            .where(IncomeModel.business_id == business_id)
            .order_by(IncomeModel.income_date.desc(), IncomeModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_income(m) for m in result.scalars().all()], total

    async def list_incomes_between(
        self, business_id: uuid.UUID, start: date, end: date
    ) -> list[IncomeRecord]:
        result = await self._session.execute(
            select(IncomeModel).where(
                IncomeModel.business_id == business_id,
                IncomeModel.status != "void",
                IncomeModel.income_date >= start,
                IncomeModel.income_date <= end,
            )
        )
        return [_income(m) for m in result.scalars().all()]

    async def void_income(self, business_id: uuid.UUID, income_id: uuid.UUID) -> IncomeRecord | None:
        row = await self._income_row(business_id, income_id)
        if row is None:
            return None
        row.status = "void"
        await self._session.flush()
        return _income(row)

    async def upsert_budget(
        self, *, business_id: uuid.UUID, category: str, category_key: str, monthly_limit: Decimal
    ) -> BudgetRecord:
        stmt = (
            pg_insert(BudgetModel)
            .values(
                id=uuid.uuid4(),
                business_id=business_id,
                category=category,
                category_key=category_key,
                monthly_limit_cents=_cents(monthly_limit),
            )
            .on_conflict_do_update(
                constraint="uq_budgets_business_category",
                set_={"monthly_limit_cents": _cents(monthly_limit), "category": category},
            )
            .returning(BudgetModel)
        )
        row = (await self._session.execute(stmt)).scalar_one()
        return _budget(row)

    async def list_budgets(self, business_id: uuid.UUID) -> list[BudgetRecord]:
        result = await self._session.execute(
            select(BudgetModel)
            .where(BudgetModel.business_id == business_id)
            .order_by(BudgetModel.category_key)
        )
        return [_budget(m) for m in result.scalars().all()]

    async def delete_budget(self, business_id: uuid.UUID, budget_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            delete(BudgetModel).where(BudgetModel.id == budget_id, BudgetModel.business_id == business_id)
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]
