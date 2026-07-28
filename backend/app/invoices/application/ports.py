from typing import Protocol

from app.invoices.domain.repository import IInvoiceRepository
from app.purchase_orders.domain.repository import IPurchaseOrderRepository


class InvoicesUnitOfWork(Protocol):
    """See identity/application/ports.py for why this Protocol exists and
    why repos are declared as `@property` rather than plain attributes.
    Includes `purchase_orders` alongside `invoices` because
    RecordOcrResultUseCase needs both to run 2-way matching.
    """

    @property
    def invoices(self) -> IInvoiceRepository: ...

    @property
    def purchase_orders(self) -> IPurchaseOrderRepository: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
