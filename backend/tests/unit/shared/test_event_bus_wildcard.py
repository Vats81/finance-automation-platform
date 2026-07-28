from app.shared.infrastructure.event_bus import InProcessEventBus


async def test_wildcard_subscriber_receives_every_event_type() -> None:
    bus = InProcessEventBus()
    received: list[tuple[str, dict]] = []

    async def audit_handler(payload: dict) -> None:
        received.append((payload.get("event_type", ""), payload))

    bus.subscribe_to_all(audit_handler)

    await bus.publish("VendorCreated", {"event_type": "VendorCreated"})
    await bus.publish("InvoiceApproved", {"event_type": "InvoiceApproved"})

    assert [event_type for event_type, _ in received] == ["VendorCreated", "InvoiceApproved"]


async def test_wildcard_and_specific_subscribers_both_fire() -> None:
    bus = InProcessEventBus()
    calls: list[str] = []

    async def specific_handler(payload: dict) -> None:
        calls.append("specific")

    async def wildcard_handler(payload: dict) -> None:
        calls.append("wildcard")

    bus.subscribe("VendorCreated", specific_handler)
    bus.subscribe_to_all(wildcard_handler)

    await bus.publish("VendorCreated", {})

    assert sorted(calls) == ["specific", "wildcard"]


async def test_wildcard_subscription_is_isolated_per_bus_instance() -> None:
    bus_a = InProcessEventBus()
    bus_b = InProcessEventBus()
    calls: list[str] = []

    async def wildcard_handler(payload: dict) -> None:
        calls.append("wildcard")

    bus_a.subscribe_to_all(wildcard_handler)

    await bus_b.publish("SomeEvent", {})  # subscribed on bus_a, not bus_b

    assert calls == []
