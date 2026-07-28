import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.bootstrap.container import get_container, get_event_bus
from app.config.settings import get_settings
from app.shared.infrastructure.outbox.outbox_model import OutboxMessageModel
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(name="app.workers.tasks.outbox_relay_task.relay_outbox_messages")
def relay_outbox_messages() -> int:
    """Polls unpublished outbox rows and dispatches each to the in-process
    event bus (see bootstrap/event_handlers.py for what's subscribed).
    Runs on Celery Beat's schedule (workers/beat_schedule.py). This is the
    ONLY writer of `published_at` — see shared/infrastructure/outbox/outbox_model.py.
    """
    return asyncio.run(_relay_outbox_messages_async())


async def _relay_outbox_messages_async() -> int:
    container = get_container()
    event_bus = get_event_bus()
    relayed = 0

    async with container.session_factory() as session:
        stmt = (
            select(OutboxMessageModel)
            .where(OutboxMessageModel.published_at.is_(None))
            .order_by(OutboxMessageModel.created_at)
            .limit(settings.outbox_relay_batch_size)
        )
        result = await session.execute(stmt)
        messages = result.scalars().all()

        for message in messages:
            try:
                # `payload` holds only the event's own fields (see
                # outbox_writer.serialize_event) — enrich with the envelope
                # fields handlers most commonly need before dispatching.
                dispatch_payload = {
                    **message.payload,
                    "aggregate_id": str(message.aggregate_id),
                    "event_id": str(message.event_id),
                    "event_type": message.event_type,
                    "occurred_at": message.occurred_at.isoformat(),
                }
                await event_bus.publish(message.event_type, dispatch_payload)
                message.published_at = datetime.now(timezone.utc)
                relayed += 1
            except Exception as exc:  # noqa: BLE001 - must not crash the relay loop
                message.attempts += 1
                message.last_error = str(exc)
                logger.exception("Failed to relay outbox message %s (%s)", message.id, message.event_type)

        await session.commit()

    return relayed
