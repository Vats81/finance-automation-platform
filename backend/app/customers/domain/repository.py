import uuid
from abc import ABC, abstractmethod

from app.customers.domain.entities import Customer


class ICustomerRepository(ABC):
    @abstractmethod
    async def get_by_id_for_business(
        self, customer_id: uuid.UUID, business_id: uuid.UUID
    ) -> Customer | None: ...

    @abstractmethod
    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Customer], int]: ...

    @abstractmethod
    def add(self, customer: Customer) -> None: ...

    @abstractmethod
    async def update(self, customer: Customer) -> None: ...
