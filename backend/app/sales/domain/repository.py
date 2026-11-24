import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from app.sales.domain.entities import Sale
from app.sales.domain.share_link import InvoiceShareLink


class ISaleRepository(ABC):
    @abstractmethod
    async def get_by_id_for_business(self, sale_id: uuid.UUID, business_id: uuid.UUID) -> Sale | None: ...

    @abstractmethod
    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Sale], int]: ...

    @abstractmethod
    async def invoice_number_in_use(
        self, business_id: uuid.UUID, invoice_number: str, *, exclude_sale_id: uuid.UUID | None = None
    ) -> bool:
        """True if a non-void sale in this business already has the number."""
        ...

    @abstractmethod
    def add(self, sale: Sale) -> None: ...

    @abstractmethod
    async def update(self, sale: Sale) -> None: ...


class IInvoiceShareLinkRepository(ABC):
    @abstractmethod
    def add(self, link: InvoiceShareLink) -> None: ...

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> InvoiceShareLink | None: ...

    @abstractmethod
    async def revoke_all_for_sale(self, sale_id: uuid.UUID, business_id: uuid.UUID, now: datetime) -> int:
        """Revokes every live link to the sale; returns how many were live."""
        ...
