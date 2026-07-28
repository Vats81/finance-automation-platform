from typing import Protocol

from app.customers.domain.repository import ICustomerRepository


class CustomersUnitOfWork(Protocol):
    """See identity/application/ports.py for why this Protocol exists and
    why repos are declared as `@property` rather than plain attributes.
    """

    @property
    def customers(self) -> ICustomerRepository: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
