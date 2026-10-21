import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.beta_waitlist.domain.status import WaitlistStatus


@dataclass(frozen=True)
class WaitlistEntry:
    id: uuid.UUID
    name: str
    work_email: str
    business_name: str | None
    business_type: str | None
    bookkeeping_method: str | None
    reporting_problem: str | None
    weekly_feedback_ok: bool
    status: WaitlistStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class IWaitlistStore(ABC):
    @abstractmethod
    async def upsert_interest(
        self,
        *,
        name: str,
        work_email: str,
        business_name: str | None,
        business_type: str | None,
        bookkeeping_method: str | None,
        reporting_problem: str | None,
        weekly_feedback_ok: bool,
    ) -> WaitlistEntry:
        """Insert, or refresh the answers of an existing entry with the same
        (case-insensitive) email without touching its status or notes."""

    @abstractmethod
    async def get(self, entry_id: uuid.UUID) -> WaitlistEntry | None: ...

    @abstractmethod
    async def list_all(self, *, limit: int) -> list[WaitlistEntry]: ...

    @abstractmethod
    async def set_status(
        self, entry_id: uuid.UUID, *, status: WaitlistStatus | None, notes: str | None
    ) -> WaitlistEntry | None: ...

    @abstractmethod
    async def delete(self, entry_id: uuid.UUID) -> bool: ...
