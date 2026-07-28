from typing import Protocol

from app.payments.domain.repository import IPaymentRepository


class PaymentsUnitOfWork(Protocol):
    """See identity/application/ports.py for why this Protocol exists and
    why repos are declared as `@property` rather than plain attributes.
    """

    @property
    def payments(self) -> IPaymentRepository: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
