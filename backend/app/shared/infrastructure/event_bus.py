import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict], Awaitable[None]]

_WILDCARD = "*"


class InProcessEventBus:
    """Simple in-process pub/sub keyed by event_type string, plus a
    wildcard channel ("*") that receives every published event regardless
    of type — used exclusively by audit/application/event_handlers.py so
    the audit trail covers every event type without bootstrap/event_handlers.py
    having to enumerate them all by hand (see subscribe_to_all).

    Consumed exclusively by the outbox relay (workers/tasks/outbox_relay_task.py):
    once a message is read from the outbox table it is dispatched here to any
    registered handlers. Handlers are registered by bounded contexts at
    startup (see app/bootstrap/event_handlers.py wiring each context's
    event_handlers module). Delivery is at-least-once — handlers must be
    idempotent (e.g. check current aggregate state before acting) since a
    handler exception on retry re-invokes every handler for that message.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    def subscribe_to_all(self, handler: EventHandler) -> None:
        self._handlers[_WILDCARD].append(handler)

    async def publish(self, event_type: str, payload: dict) -> None:
        handlers = self._handlers.get(event_type, []) + self._handlers.get(_WILDCARD, [])
        if not handlers:
            logger.debug("No subscribers for event_type=%s", event_type)
            return
        for handler in handlers:
            await handler(payload)
