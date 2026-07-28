import uuid
from datetime import datetime

from app.audit.application.commands.record_audit_entry import RecordAuditEntryCommand, RecordAuditEntryUseCase


async def handle_any_event(payload: dict) -> None:
    """Subscribed to the event bus's wildcard channel (see
    bootstrap/event_handlers.py:register_all_event_handlers using
    event_bus.subscribe_to_all) so every domain event across every
    context is recorded, with no per-event-type registration needed.

    Imports bootstrap.container lazily: this module is pulled in by
    bootstrap/event_handlers.py, which container.py itself imports.
    """
    from app.bootstrap.container import get_container
    from app.bootstrap.unit_of_work import AppUnitOfWork

    container = get_container()

    async with container.session_factory() as session:
        uow = AppUnitOfWork(session)
        use_case = RecordAuditEntryUseCase(uow)
        await use_case.execute(
            RecordAuditEntryCommand(
                event_type=payload["event_type"],
                aggregate_id=uuid.UUID(payload["aggregate_id"]),
                payload=payload,
                occurred_at=datetime.fromisoformat(payload["occurred_at"]),
            )
        )
