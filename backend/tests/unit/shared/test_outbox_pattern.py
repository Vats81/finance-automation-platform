import uuid
from dataclasses import dataclass

import pytest

from app.shared.domain.domain_event import DomainEvent
from app.shared.infrastructure.event_bus import InProcessEventBus
from app.shared.infrastructure.outbox.outbox_writer import serialize_event


@dataclass(frozen=True, kw_only=True)
class SampleEvent(DomainEvent):
    name: str
    amount_cents: int


def test_serialize_event_excludes_envelope_fields_and_is_json_safe() -> None:
    event = SampleEvent(aggregate_id=uuid.uuid4(), name="widget", amount_cents=1050)

    payload = serialize_event(event)

    assert payload == {"name": "widget", "amount_cents": 1050}
    assert "event_id" not in payload
    assert "aggregate_id" not in payload
    assert "occurred_at" not in payload


async def test_event_bus_dispatches_to_registered_handler() -> None:
    bus = InProcessEventBus()
    received: list[dict] = []

    async def handler(payload: dict) -> None:
        received.append(payload)

    bus.subscribe("SampleEvent", handler)
    await bus.publish("SampleEvent", {"name": "widget"})

    assert received == [{"name": "widget"}]


async def test_event_bus_publish_with_no_subscribers_is_a_noop() -> None:
    bus = InProcessEventBus()

    await bus.publish("NoOneListensToThis", {"foo": "bar"})  # must not raise


async def test_event_bus_dispatches_to_all_registered_handlers_for_same_event() -> None:
    bus = InProcessEventBus()
    calls: list[str] = []

    async def handler_a(payload: dict) -> None:
        calls.append("a")

    async def handler_b(payload: dict) -> None:
        calls.append("b")

    bus.subscribe("SampleEvent", handler_a)
    bus.subscribe("SampleEvent", handler_b)
    await bus.publish("SampleEvent", {})

    assert calls == ["a", "b"]


async def test_event_bus_propagates_handler_exception_for_relay_retry() -> None:
    """The outbox relay task relies on publish() raising so it can leave
    published_at unset and record the error for retry — see
    workers/tasks/outbox_relay_task.py.
    """
    bus = InProcessEventBus()

    async def failing_handler(payload: dict) -> None:
        raise RuntimeError("boom")

    bus.subscribe("SampleEvent", failing_handler)

    with pytest.raises(RuntimeError):
        await bus.publish("SampleEvent", {})
