import uuid
from abc import ABC, abstractmethod

from app.expenses.domain.entities import Expense


class IExpenseRepository(ABC):
    @abstractmethod
    async def get_by_id_for_business(
        self, expense_id: uuid.UUID, business_id: uuid.UUID
    ) -> Expense | None: ...

    @abstractmethod
    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Expense], int]: ...

    @abstractmethod
    def add(self, expense: Expense) -> None: ...

    @abstractmethod
    async def update(self, expense: Expense) -> None: ...
