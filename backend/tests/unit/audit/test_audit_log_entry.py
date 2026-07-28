import uuid
from datetime import datetime, timezone

from app.audit.domain.entities import AuditLogEntry


def test_record_captures_event_details_and_stamps_recorded_at() -> None:
    aggregate_id = uuid.uuid4()
    occurred_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    entry = AuditLogEntry.record(
        event_type="VendorCreated",
        aggregate_id=aggregate_id,
        payload={"legal_name": "Acme"},
        occurred_at=occurred_at,
    )

    assert entry.event_type == "VendorCreated"
    assert entry.aggregate_id == aggregate_id
    assert entry.payload == {"legal_name": "Acme"}
    assert entry.occurred_at == occurred_at
    assert entry.recorded_at >= occurred_at


def test_two_entries_have_distinct_ids() -> None:
    entry_a = AuditLogEntry.record(
        event_type="X", aggregate_id=uuid.uuid4(), payload={}, occurred_at=datetime.now(timezone.utc)
    )
    entry_b = AuditLogEntry.record(
        event_type="X", aggregate_id=uuid.uuid4(), payload={}, occurred_at=datetime.now(timezone.utc)
    )

    assert entry_a.id != entry_b.id
