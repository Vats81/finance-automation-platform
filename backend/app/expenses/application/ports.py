from typing import Protocol

from app.expenses.domain.repository import IExpenseRepository


class ExpensesUnitOfWork(Protocol):
    """See identity/application/ports.py for why this Protocol exists and
    why repos are declared as `@property` rather than plain attributes.
    """

    @property
    def expenses(self) -> IExpenseRepository: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
