from typing import Protocol

from app.purchase_orders.domain.repository import IPurchaseOrderRepository


class PurchaseOrdersUnitOfWork(Protocol):
    """See identity/application/ports.py for why this Protocol exists and
    why repos are declared as `@property` rather than plain attributes.
    """

    @property
    def purchase_orders(self) -> IPurchaseOrderRepository: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
