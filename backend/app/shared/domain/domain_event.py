import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base class for all domain events raised by aggregates.

    `event_id` gives handlers a stable dedupe key for at-least-once delivery
    through the outbox relay. `aggregate_id` and `event_type` are read by the
    outbox writer without needing to know about each event subclass.
    """

    # aggregate_id is kw_only=False so every subclass can pass it
    # positionally (e.g. `VendorCreated(vendor.id, legal_name=...)`); mypy's
    # dataclass plugin doesn't model kw_only field reordering the same way
    # the runtime does (verified: this construction pattern works correctly
    # at runtime), hence the targeted ignore.
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    aggregate_id: uuid.UUID = field(kw_only=False)  # type: ignore[misc]

    @property
    def event_type(self) -> str:
        return type(self).__name__
