import uuid
from datetime import datetime

from pydantic import BaseModel

from app.audit.domain.entities import AuditLogEntry


class AuditLogEntryResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    aggregate_id: uuid.UUID
    payload: dict
    occurred_at: datetime
    recorded_at: datetime

    @classmethod
    def from_domain(cls, entry: AuditLogEntry) -> "AuditLogEntryResponse":
        return cls(
            id=entry.id,
            event_type=entry.event_type,
            aggregate_id=entry.aggregate_id,
            payload=entry.payload,
            occurred_at=entry.occurred_at,
            recorded_at=entry.recorded_at,
        )


class PagedAuditLogResponse(BaseModel):
    items: list[AuditLogEntryResponse]
    total: int
    offset: int
    limit: int
