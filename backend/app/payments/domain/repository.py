import uuid
from abc import ABC, abstractmethod

from app.payments.domain.entities import Payment


class IPaymentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, payment_id: uuid.UUID) -> Payment | None: ...

    @abstractmethod
    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[Payment], int]: ...

    @abstractmethod
    def add(self, payment: Payment) -> None: ...

    @abstractmethod
    async def update(self, payment: Payment) -> None: ...
