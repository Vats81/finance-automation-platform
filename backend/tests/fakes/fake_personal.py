import uuid
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

from app.personal_finance.application.ports import BudgetRecord, IncomeRecord, IPersonalFinanceRepository


class FakePersonalFinanceRepository(IPersonalFinanceRepository):
    def __init__(self) -> None:
        self.incomes: dict[uuid.UUID, IncomeRecord] = {}
        self.budgets: dict[uuid.UUID, tuple[BudgetRecord, str]] = {}  # id -> (record, category_key)

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
        record = IncomeRecord(
            id=uuid.uuid4(),
            business_id=business_id,
            income_date=income_date,
            source=source,
            category=category,
            amount=amount,
            notes=notes,
            status="recorded",
            created_at=datetime.now(timezone.utc),
        )
        self.incomes[record.id] = record
        return record

    async def get_income(self, business_id: uuid.UUID, income_id: uuid.UUID) -> IncomeRecord | None:
        record = self.incomes.get(income_id)
        return record if record is not None and record.business_id == business_id else None

    async def list_incomes(
        self, business_id: uuid.UUID, *, offset: int, limit: int
    ) -> tuple[list[IncomeRecord], int]:
        rows = sorted(
            (r for r in self.incomes.values() if r.business_id == business_id),
            key=lambda r: (r.income_date, r.created_at),
            reverse=True,
        )
        return rows[offset : offset + limit], len(rows)

    async def list_incomes_between(
        self, business_id: uuid.UUID, start: date, end: date
    ) -> list[IncomeRecord]:
        return [
            r
            for r in self.incomes.values()
            if r.business_id == business_id and r.status != "void" and start <= r.income_date <= end
        ]

    async def void_income(self, business_id: uuid.UUID, income_id: uuid.UUID) -> IncomeRecord | None:
        record = await self.get_income(business_id, income_id)
        if record is None:
            return None
        voided = replace(record, status="void")
        self.incomes[income_id] = voided
        return voided

    async def upsert_budget(
        self, *, business_id: uuid.UUID, category: str, category_key: str, monthly_limit: Decimal
    ) -> BudgetRecord:
        for budget_id, (record, key) in self.budgets.items():
            if record.business_id == business_id and key == category_key:
                updated = replace(record, category=category, monthly_limit=monthly_limit)
                self.budgets[budget_id] = (updated, key)
                return updated
        record = BudgetRecord(
            id=uuid.uuid4(),
            business_id=business_id,
            category=category,
            monthly_limit=monthly_limit,
            created_at=datetime.now(timezone.utc),
        )
        self.budgets[record.id] = (record, category_key)
        return record

    async def list_budgets(self, business_id: uuid.UUID) -> list[BudgetRecord]:
        return sorted(
            (r for r, _ in self.budgets.values() if r.business_id == business_id),
            key=lambda r: r.category.lower(),
        )

    async def delete_budget(self, business_id: uuid.UUID, budget_id: uuid.UUID) -> bool:
        entry = self.budgets.get(budget_id)
        if entry is None or entry[0].business_id != business_id:
            return False
        del self.budgets[budget_id]
        return True
