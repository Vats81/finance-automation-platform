import uuid
from abc import ABC, abstractmethod

from app.audit.domain.entities import AuditLogEntry


class IAuditLogRepository(ABC):
    """No `update` — audit entries are append-only and never mutated."""

    @abstractmethod
    def add(self, entry: AuditLogEntry) -> None: ...

    @abstractmethod
    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[AuditLogEntry], int]: ...

    @abstractmethod
    async def list_for_aggregate(
        self, aggregate_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[AuditLogEntry], int]: ...
