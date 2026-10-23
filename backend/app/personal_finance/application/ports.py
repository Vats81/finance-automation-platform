import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class IncomeRecord:
    id: uuid.UUID
    business_id: uuid.UUID
    income_date: date
    source: str
    category: str
    amount: Decimal
    notes: str | None
    status: str  # "recorded" | "void"
    created_at: datetime


@dataclass(frozen=True)
class BudgetRecord:
    id: uuid.UUID
    business_id: uuid.UUID
    category: str
    monthly_limit: Decimal
    created_at: datetime


class IPersonalFinanceRepository(ABC):
    """Income and budget records of personal workspaces. Every method is scoped
    by business_id, so one workspace can never read or change another's.
    """

    @abstractmethod
    async def add_income(
        self,
        *,
        business_id: uuid.UUID,
        income_date: date,
        source: str,
        category: str,
        amount: Decimal,
        notes: str | None,
    ) -> IncomeRecord: ...

    @abstractmethod
    async def get_income(self, business_id: uuid.UUID, income_id: uuid.UUID) -> IncomeRecord | None: ...

    @abstractmethod
    async def list_incomes(
        self, business_id: uuid.UUID, *, offset: int, limit: int
    ) -> tuple[list[IncomeRecord], int]: ...

    @abstractmethod
    async def list_incomes_between(
        self, business_id: uuid.UUID, start: date, end: date
    ) -> list[IncomeRecord]:
        """Recorded (not void) income dated within [start, end]."""

    @abstractmethod
    async def void_income(self, business_id: uuid.UUID, income_id: uuid.UUID) -> IncomeRecord | None: ...

    @abstractmethod
    async def upsert_budget(
        self, *, business_id: uuid.UUID, category: str, category_key: str, monthly_limit: Decimal
    ) -> BudgetRecord: ...

    @abstractmethod
    async def list_budgets(self, business_id: uuid.UUID) -> list[BudgetRecord]: ...

    @abstractmethod
    async def delete_budget(self, business_id: uuid.UUID, budget_id: uuid.UUID) -> bool: ...
