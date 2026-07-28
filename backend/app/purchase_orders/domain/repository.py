import uuid
from abc import ABC, abstractmethod

from app.purchase_orders.domain.entities import PurchaseOrder


class IPurchaseOrderRepository(ABC):
    @abstractmethod
    async def get_by_id(self, po_id: uuid.UUID) -> PurchaseOrder | None: ...

    @abstractmethod
    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[PurchaseOrder], int]: ...

    @abstractmethod
    def add(self, purchase_order: PurchaseOrder) -> None: ...

    @abstractmethod
    async def update(self, purchase_order: PurchaseOrder) -> None: ...
