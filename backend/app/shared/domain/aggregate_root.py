from app.shared.domain.base_entity import Entity
from app.shared.domain.domain_event import DomainEvent


class AggregateRoot(Entity):
    """Base class for aggregate roots.

    Aggregates record domain events on themselves as invariants change
    (`_record_event`). The Unit of Work pulls these off via `pull_domain_events`
    at commit time and writes them to the outbox in the same transaction as the
    state change, so cross-aggregate/cross-context consistency never depends on
    a dual write. See shared/infrastructure/outbox/outbox_writer.py.
    """

    def __init__(self, entity_id=None) -> None:
        super().__init__(entity_id)
        self._domain_events: list[DomainEvent] = []
        self.version: int = 0

    def _record_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)

    def pull_domain_events(self) -> list[DomainEvent]:
        events = list(self._domain_events)
        self._domain_events.clear()
        return events

    @property
    def has_pending_events(self) -> bool:
        return len(self._domain_events) > 0
