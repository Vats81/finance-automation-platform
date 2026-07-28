from typing import Protocol

from app.vendors.domain.repository import IVendorRepository


class VendorsUnitOfWork(Protocol):
    """See identity/application/ports.py for why this Protocol exists and
    why repos are declared as `@property` rather than plain attributes.
    """

    @property
    def vendors(self) -> IVendorRepository: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
