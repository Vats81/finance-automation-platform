import uuid
from dataclasses import dataclass
from datetime import datetime

from app.audit.application.ports import AuditUnitOfWork
from app.audit.domain.entities import AuditLogEntry


@dataclass(frozen=True)
class RecordAuditEntryCommand:
    event_type: str
    aggregate_id: uuid.UUID
    payload: dict
    occurred_at: datetime


class RecordAuditEntryUseCase:
    def __init__(self, uow: AuditUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: RecordAuditEntryCommand) -> AuditLogEntry:
        entry = AuditLogEntry.record(
            event_type=command.event_type,
            aggregate_id=command.aggregate_id,
            payload=command.payload,
            occurred_at=command.occurred_at,
        )
        self._uow.audit_log.add(entry)
        await self._uow.commit()
        return entry
