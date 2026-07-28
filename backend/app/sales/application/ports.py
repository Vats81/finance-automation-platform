from typing import Protocol

from app.sales.domain.repository import ISaleRepository


class SalesUnitOfWork(Protocol):
    """See identity/application/ports.py for why this Protocol exists and
    why repos are declared as `@property` rather than plain attributes.
    """

    @property
    def sales(self) -> ISaleRepository: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
