import uuid
from abc import ABC, abstractmethod

from app.sales.domain.entities import Sale


class ISaleRepository(ABC):
    @abstractmethod
    async def get_by_id_for_business(self, sale_id: uuid.UUID, business_id: uuid.UUID) -> Sale | None: ...

    @abstractmethod
    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Sale], int]: ...

    @abstractmethod
    def add(self, sale: Sale) -> None: ...

    @abstractmethod
    async def update(self, sale: Sale) -> None: ...
