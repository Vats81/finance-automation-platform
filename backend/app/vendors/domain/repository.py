import uuid
from abc import ABC, abstractmethod

from app.vendors.domain.entities import Vendor


class IVendorRepository(ABC):
    @abstractmethod
    async def get_by_id(self, vendor_id: uuid.UUID) -> Vendor | None: ...

    @abstractmethod
    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[Vendor], int]: ...

    @abstractmethod
    async def get_by_id_for_business(self, vendor_id: uuid.UUID, business_id: uuid.UUID) -> Vendor | None:
        """Strictly tenant-scoped lookup for the SMB product: returns None
        (not the vendor) if it belongs to a different business or has no
        business_id at all, so one business can never fetch another's
        vendor — or an AP-automation vendor — by guessing an id.
        """
        ...

    @abstractmethod
    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Vendor], int]: ...

    @abstractmethod
    def add(self, vendor: Vendor) -> None: ...

    @abstractmethod
    async def update(self, vendor: Vendor) -> None: ...
