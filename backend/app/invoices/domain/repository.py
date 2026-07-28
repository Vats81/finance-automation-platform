import uuid
from abc import ABC, abstractmethod

from app.invoices.domain.entities import Invoice


class IInvoiceRepository(ABC):
    @abstractmethod
    async def get_by_id(self, invoice_id: uuid.UUID) -> Invoice | None: ...

    @abstractmethod
    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[Invoice], int]: ...

    @abstractmethod
    def add(self, invoice: Invoice) -> None: ...

    @abstractmethod
    async def update(self, invoice: Invoice) -> None: ...
