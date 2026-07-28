from typing import Protocol

from app.purchases.domain.repository import IPurchaseRepository


class PurchasesUnitOfWork(Protocol):
    """See identity/application/ports.py for why this Protocol exists and
    why repos are declared as `@property` rather than plain attributes.
    """

    @property
    def purchases(self) -> IPurchaseRepository: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
