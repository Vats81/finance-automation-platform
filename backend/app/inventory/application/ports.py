from typing import Protocol

from app.inventory.domain.repository import IProductRepository


class InventoryUnitOfWork(Protocol):
    """See identity/application/ports.py for why this Protocol exists and
    why repos are declared as `@property` rather than plain attributes.
    """

    @property
    def products(self) -> IProductRepository: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
