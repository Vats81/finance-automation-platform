import dataclasses
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.domain.domain_event import DomainEvent
from app.shared.infrastructure.outbox.outbox_model import OutboxMessageModel


def _to_json_safe(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {k: _to_json_safe(v) for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _to_json_safe(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
        return [_to_json_safe(v) for v in value]
    return value


_ENVELOPE_FIELDS = {"event_id", "occurred_at", "aggregate_id"}


def serialize_event(event: DomainEvent) -> dict:
    payload = {k: v for k, v in dataclasses.asdict(event).items() if k not in _ENVELOPE_FIELDS}
    return _to_json_safe(payload)


async def write_event_to_outbox(session: AsyncSession, event: DomainEvent) -> None:
    """Appends an OutboxMessageModel row to the session (not yet committed).

    Must be called within the same transaction as the aggregate's state
    change so the write is atomic — see SqlAlchemyUnitOfWork.commit().
    """
    row = OutboxMessageModel(
        event_id=event.event_id,
        event_type=event.event_type,
        aggregate_id=event.aggregate_id,
        payload=serialize_event(event),
        occurred_at=event.occurred_at,
    )
    session.add(row)
