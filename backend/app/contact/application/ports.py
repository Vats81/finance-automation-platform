import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ContactRequest:
    id: uuid.UUID
    name: str
    email: str
    business_name: str | None
    message: str | None
    notified: bool
    created_at: datetime


class IContactRequestStore(ABC):
    """Persistence for landing-page demo requests. A port (rather than the
    shared AppUnitOfWork) because this context is tiny and standalone: no
    aggregate, no domain events, nothing transactional with any other
    context. Commits on its own, so the request is durably saved before
    anything that can fail (like sending email) is attempted.
    """

    @abstractmethod
    async def add(
        self, *, name: str, email: str, business_name: str | None, message: str | None
    ) -> ContactRequest: ...

    @abstractmethod
    async def mark_notified(self, request_id: uuid.UUID) -> None: ...

    @abstractmethod
    async def list_recent(self, *, limit: int) -> list[ContactRequest]: ...
