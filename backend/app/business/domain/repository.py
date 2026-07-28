import uuid
from abc import ABC, abstractmethod

from app.business.domain.entities import Business, BusinessMembership


class IBusinessRepository(ABC):
    @abstractmethod
    async def get_by_id(self, business_id: uuid.UUID) -> Business | None: ...

    @abstractmethod
    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[Business], int]:
        """Every business on the platform — used only by the Admin Panel,
        which is deliberately not business-scoped.
        """
        ...

    @abstractmethod
    def add(self, business: Business) -> None: ...

    @abstractmethod
    async def update(self, business: Business) -> None: ...


class IBusinessMembershipRepository(ABC):
    @abstractmethod
    async def get_by_id(self, membership_id: uuid.UUID) -> BusinessMembership | None: ...

    @abstractmethod
    async def get_for_user_and_business(
        self, *, user_id: uuid.UUID, business_id: uuid.UUID
    ) -> BusinessMembership | None: ...

    @abstractmethod
    async def list_for_user(self, user_id: uuid.UUID) -> list[BusinessMembership]:
        """Every active membership for a user — drives 'my businesses' /
        the business switcher, and 'manage multiple businesses ... from one
        account' from the spec.
        """
        ...

    @abstractmethod
    async def list_for_business(self, business_id: uuid.UUID) -> list[BusinessMembership]:
        """Every membership for a business (active, invited, and removed —
        the Team Members page shows status badges rather than hiding
        removed rows, same convention as voided Sales/Purchases/Expenses).
        """
        ...

    @abstractmethod
    def add(self, membership: BusinessMembership) -> None: ...

    @abstractmethod
    async def update(self, membership: BusinessMembership) -> None: ...
