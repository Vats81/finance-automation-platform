import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class AuditLogEntry:
    """A plain append-only record, not a full aggregate — it has no
    invariants to protect and is never mutated after creation, so it
    doesn't need AggregateRoot's event-collection machinery. Recorded for
    every domain event across every context (see
    audit/application/event_handlers.py, subscribed to the event bus's
    wildcard channel — bootstrap/event_handlers.py).
    """

    event_type: str
    aggregate_id: uuid.UUID
    payload: dict
    occurred_at: datetime
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def record(
        cls, *, event_type: str, aggregate_id: uuid.UUID, payload: dict, occurred_at: datetime
    ) -> "AuditLogEntry":
        return cls(event_type=event_type, aggregate_id=aggregate_id, payload=payload, occurred_at=occurred_at)
