from typing import Protocol

from app.business.domain.repository import IBusinessMembershipRepository, IBusinessRepository


class BusinessUnitOfWork(Protocol):
    """See identity/application/ports.py for why this Protocol exists and
    why repos are declared as `@property` rather than plain attributes.
    """

    @property
    def businesses(self) -> IBusinessRepository: ...

    @property
    def business_memberships(self) -> IBusinessMembershipRepository: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
