import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.firms.domain.value_objects import FirmMembershipStatus, FirmRole, FirmStatus


@dataclass(frozen=True)
class FirmRecord:
    id: uuid.UUID
    name: str
    owner_user_id: uuid.UUID
    status: FirmStatus
    created_at: datetime


@dataclass(frozen=True)
class FirmMemberRecord:
    id: uuid.UUID
    firm_id: uuid.UUID
    user_id: uuid.UUID
    role: FirmRole
    status: FirmMembershipStatus
    invited_by_user_id: uuid.UUID | None
    joined_at: datetime | None

    @property
    def is_active(self) -> bool:
        return self.status == FirmMembershipStatus.ACTIVE


class IFirmRepository(ABC):
    """Persistence for firms and their staff. Changes are made through the
    shared unit of work, so a use case commits once at its end.
    """

    @abstractmethod
    async def create_firm(self, *, name: str, owner_user_id: uuid.UUID) -> FirmRecord:
        """Creates the firm and its owner's membership together."""

    @abstractmethod
    async def get_firm(self, firm_id: uuid.UUID) -> FirmRecord | None: ...

    @abstractmethod
    async def get_membership(self, firm_id: uuid.UUID, user_id: uuid.UUID) -> FirmMemberRecord | None:
        """The user's membership in that firm in any status (None if never a member)."""

    @abstractmethod
    async def get_membership_by_id(self, membership_id: uuid.UUID) -> FirmMemberRecord | None: ...

    @abstractmethod
    async def list_active_memberships_for_user(self, user_id: uuid.UUID) -> list[FirmMemberRecord]: ...

    @abstractmethod
    async def list_members(self, firm_id: uuid.UUID) -> list[FirmMemberRecord]:
        """Every membership of the firm, removed ones included."""

    @abstractmethod
    async def add_member(
        self, *, firm_id: uuid.UUID, user_id: uuid.UUID, role: FirmRole, invited_by_user_id: uuid.UUID
    ) -> FirmMemberRecord: ...

    @abstractmethod
    async def update_member(
        self,
        membership_id: uuid.UUID,
        *,
        role: FirmRole | None = None,
        status: FirmMembershipStatus | None = None,
        invited_by_user_id: uuid.UUID | None = None,
    ) -> FirmMemberRecord | None: ...

    @abstractmethod
    async def last_activity_by_business(self, business_ids: list[uuid.UUID]) -> dict[uuid.UUID, datetime]:
        """Most recent recorded change per business (from the audit trail)."""
