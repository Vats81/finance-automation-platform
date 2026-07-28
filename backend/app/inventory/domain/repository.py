import uuid
from abc import ABC, abstractmethod

from app.inventory.domain.entities import Product


class IProductRepository(ABC):
    @abstractmethod
    async def get_by_id_for_business(
        self, product_id: uuid.UUID, business_id: uuid.UUID
    ) -> Product | None: ...

    @abstractmethod
    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Product], int]: ...

    @abstractmethod
    def add(self, product: Product) -> None: ...

    @abstractmethod
    async def update(self, product: Product) -> None: ...
