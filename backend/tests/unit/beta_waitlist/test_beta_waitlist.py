import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.exception_handlers import register_exception_handlers
from app.api.rate_limit import limiter
from app.beta_waitlist.api.routes import admin_router, get_waitlist_store, router
from app.beta_waitlist.application.ports import IWaitlistStore, WaitlistEntry
from app.beta_waitlist.application.use_cases import WaitlistEntryNotFoundException, update_entry
from app.beta_waitlist.domain.status import (
    ALLOWED_TRANSITIONS,
    InvalidWaitlistTransitionException,
    WaitlistStatus,
    check_transition,
)
from app.identity.api.dependencies import require_platform_admin


class MemoryStore(IWaitlistStore):
    def __init__(self) -> None:
        self.rows: dict[uuid.UUID, WaitlistEntry] = {}

    async def upsert_interest(self, **kw: object) -> WaitlistEntry:
        email = str(kw["work_email"]).lower()
        existing = next((e for e in self.rows.values() if e.work_email == email), None)
        now = datetime.now(timezone.utc)
        entry = WaitlistEntry(
            id=existing.id if existing else uuid.uuid4(),
            name=str(kw["name"]),
            work_email=email,
            business_name=kw["business_name"],  # type: ignore[arg-type]
            business_type=kw["business_type"],  # type: ignore[arg-type]
            bookkeeping_method=kw["bookkeeping_method"],  # type: ignore[arg-type]
            reporting_problem=kw["reporting_problem"],  # type: ignore[arg-type]
            weekly_feedback_ok=bool(kw["weekly_feedback_ok"]),
            status=existing.status if existing else WaitlistStatus.INTERESTED,
            notes=existing.notes if existing else None,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        self.rows[entry.id] = entry
        return entry

    async def get(self, entry_id: uuid.UUID) -> WaitlistEntry | None:
        return self.rows.get(entry_id)

    async def get_by_email(self, work_email: str) -> WaitlistEntry | None:
        return next((e for e in self.rows.values() if e.work_email == work_email.strip().lower()), None)

    async def list_all(self, *, limit: int) -> list[WaitlistEntry]:
        return list(self.rows.values())[:limit]

    async def set_status(
        self, entry_id: uuid.UUID, *, status: WaitlistStatus | None, notes: str | None
    ) -> WaitlistEntry | None:
        current = self.rows.get(entry_id)
        if current is None:
            return None
        updated = WaitlistEntry(
            **{
                **current.__dict__,
                "status": status or current.status,
                "notes": current.notes if notes is None else notes,
            }
        )
        self.rows[entry_id] = updated
        return updated

    async def delete(self, entry_id: uuid.UUID) -> bool:
        return self.rows.pop(entry_id, None) is not None


@pytest.fixture
def api() -> tuple[TestClient, MemoryStore, FastAPI]:
    limiter.enabled = False
    store = MemoryStore()
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.dependency_overrides[get_waitlist_store] = lambda: store
    yield TestClient(app, raise_server_exceptions=False), store, app
    limiter.enabled = True


_GOOD = {
    "name": "Asha Rao",
    "work_email": "Asha@Example.com",
    "business_type": "Home bakery",
    "bookkeeping_method": "spreadsheet",
    "reporting_problem": "I never know my monthly profit",
    "weekly_feedback_ok": True,
    "acknowledged": True,
}


def test_joining_registers_interest_only(api: tuple[TestClient, MemoryStore, FastAPI]) -> None:
    client, store, _ = api

    response = client.post("/api/v1/beta-waitlist", json=_GOOD)

    assert response.status_code == 201 and response.json() == {"received": True}
    (entry,) = store.rows.values()
    assert entry.work_email == "asha@example.com"
    assert entry.status == WaitlistStatus.INTERESTED


def test_the_visitor_must_acknowledge_the_private_beta_terms(
    api: tuple[TestClient, MemoryStore, FastAPI],
) -> None:
    client, store, _ = api

    assert client.post("/api/v1/beta-waitlist", json={**_GOOD, "acknowledged": False}).status_code == 422
    missing = {k: v for k, v in _GOOD.items() if k != "acknowledged"}
    assert client.post("/api/v1/beta-waitlist", json=missing).status_code == 422
    assert store.rows == {}


def test_a_returning_email_looks_identical_and_keeps_its_status(
    api: tuple[TestClient, MemoryStore, FastAPI],
) -> None:
    client, store, _ = api
    first = client.post("/api/v1/beta-waitlist", json=_GOOD)
    entry = next(iter(store.rows.values()))
    store.rows[entry.id] = WaitlistEntry(**{**entry.__dict__, "status": WaitlistStatus.QUALIFIED})

    again = client.post("/api/v1/beta-waitlist", json={**_GOOD, "name": "Asha R."})

    assert again.status_code == first.status_code == 201 and again.json() == first.json()
    (only,) = store.rows.values()
    assert only.name == "Asha R." and only.status == WaitlistStatus.QUALIFIED


def test_a_filled_honeypot_is_dropped_silently(api: tuple[TestClient, MemoryStore, FastAPI]) -> None:
    client, store, _ = api

    response = client.post("/api/v1/beta-waitlist", json={**_GOOD, "website": "http://spam.example"})

    assert response.status_code == 201
    assert store.rows == {}


def test_bad_input_is_rejected_cleanly(api: tuple[TestClient, MemoryStore, FastAPI]) -> None:
    client, _, _ = api

    assert client.post("/api/v1/beta-waitlist", json={**_GOOD, "work_email": "nope"}).status_code == 422
    assert client.post("/api/v1/beta-waitlist", json={**_GOOD, "name": ""}).status_code == 422
    assert (
        client.post("/api/v1/beta-waitlist", json={**_GOOD, "reporting_problem": "x" * 1001}).status_code
        == 422
    )


def test_the_admin_endpoints_require_a_platform_admin(api: tuple[TestClient, MemoryStore, FastAPI]) -> None:
    client, _, _ = api

    assert client.get("/api/v1/admin/beta-waitlist").status_code in (401, 403)
    assert client.patch(
        f"/api/v1/admin/beta-waitlist/{uuid.uuid4()}", json={"status": "qualified"}
    ).status_code in (
        401,
        403,
    )


def test_an_admin_can_review_and_move_entries_through_the_pipeline(
    api: tuple[TestClient, MemoryStore, FastAPI],
) -> None:
    client, store, app = api
    client.post("/api/v1/beta-waitlist", json=_GOOD)
    entry_id = next(iter(store.rows))
    app.dependency_overrides[require_platform_admin] = lambda: object()
    base = f"/api/v1/admin/beta-waitlist/{entry_id}"

    listed = client.get("/api/v1/admin/beta-waitlist").json()
    assert [e["status"] for e in listed] == ["interested"]

    assert client.patch(base, json={"status": "invited"}).status_code == 422  # must be qualified first
    assert (
        client.patch(base, json={"status": "qualified", "notes": "Call booked"}).json()["notes"]
        == "Call booked"
    )
    assert client.patch(base, json={"status": "invited"}).json()["status"] == "invited"
    assert (
        client.patch(f"/api/v1/admin/beta-waitlist/{uuid.uuid4()}", json={"status": "paused"}).status_code
        == 404
    )
    assert client.delete(base).status_code == 204
    assert client.delete(base).status_code == 404


def test_the_pipeline_cannot_skip_to_invited_or_onboarded() -> None:
    for target in (WaitlistStatus.INVITED, WaitlistStatus.ONBOARDED, WaitlistStatus.WAITING_FOR_CHECKS):
        with pytest.raises(InvalidWaitlistTransitionException):
            check_transition(WaitlistStatus.INTERESTED, target)
    with pytest.raises(InvalidWaitlistTransitionException):
        check_transition(WaitlistStatus.QUALIFIED, WaitlistStatus.ONBOARDED)
    check_transition(WaitlistStatus.QUALIFIED, WaitlistStatus.QUALIFIED)  # no-op is fine


def test_every_status_has_a_defined_set_of_next_steps() -> None:
    assert set(ALLOWED_TRANSITIONS) == set(WaitlistStatus)
    assert all(
        WaitlistStatus.PAUSED in nxt for s, nxt in ALLOWED_TRANSITIONS.items() if s != WaitlistStatus.PAUSED
    )


async def test_updating_a_missing_entry_is_not_found() -> None:
    with pytest.raises(WaitlistEntryNotFoundException):
        await update_entry(MemoryStore(), uuid.uuid4(), status=WaitlistStatus.PAUSED, notes=None)
