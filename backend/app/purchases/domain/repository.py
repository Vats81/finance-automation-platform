import uuid
from abc import ABC, abstractmethod

from app.purchases.domain.entities import Purchase


class IPurchaseRepository(ABC):
    @abstractmethod
    async def get_by_id_for_business(
        self, purchase_id: uuid.UUID, business_id: uuid.UUID
    ) -> Purchase | None: ...

    @abstractmethod
    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Purchase], int]: ...

    @abstractmethod
    def add(self, purchase: Purchase) -> None: ...

    @abstractmethod
    async def update(self, purchase: Purchase) -> None: ...
