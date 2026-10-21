"""Idempotency-Key behaviour, against an in-memory store and a toy endpoint.

(The SQL-backed store is exercised against production by the live check; this
covers the protocol: replay, in-flight, reuse, failures, scoping.)
"""

import asyncio
import uuid

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.idempotency import _KEEP_HOURS, Claim, IdempotencyMiddleware, Stored

BIZ = str(uuid.uuid4())
URL = f"/api/v1/businesses/{BIZ}/things"


class MemoryStore:
    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    async def claim(self, key_hash: str, request_hash: str) -> Claim:
        row = self.rows.get(key_hash)
        if row is None:
            self.rows[key_hash] = {"request_hash": request_hash, "state": "pending", "stored": None}
            return Claim("new")
        if row["request_hash"] != request_hash:
            return Claim("mismatch")
        if row["state"] == "done":
            return Claim("replay", row["stored"])
        return Claim("in_progress")

    async def complete(self, key_hash: str, stored: Stored) -> None:
        self.rows[key_hash].update(state="done", stored=stored)

    async def release(self, key_hash: str) -> None:
        self.rows.pop(key_hash, None)


def make_app(delay: float = 0.0) -> tuple[FastAPI, MemoryStore, list[dict]]:
    app = FastAPI()
    store = MemoryStore()
    created: list[dict] = []
    app.state.idempotency_store = store
    app.add_middleware(IdempotencyMiddleware)

    @app.post("/api/v1/businesses/{business_id}/things", status_code=201)
    async def create(business_id: str, body: dict) -> dict:
        if delay:
            await asyncio.sleep(delay)
        if body.get("fail"):
            raise HTTPException(status_code=422, detail="bad input")
        item = {"id": len(created) + 1, "name": body.get("name")}
        created.append(item)
        return item

    @app.post("/api/v1/other")
    async def other() -> dict:
        created.append({"other": True})
        return {"ok": True}

    return app, store, created


def post(
    client: TestClient, key: str | None = "k1", token: str = "Bearer a", **body: object
) -> httpx.Response:
    headers = {"Authorization": token}
    if key is not None:
        headers["Idempotency-Key"] = key
    return client.post(URL, headers=headers, json=body or {"name": "sale"})


def test_a_repeat_with_the_same_key_replays_the_first_response_and_creates_nothing_new() -> None:
    app, _, created = make_app()
    client = TestClient(app)

    first, second, third = post(client), post(client), post(client)

    assert first.status_code == second.status_code == third.status_code == 201
    assert first.json() == second.json() == third.json() == {"id": 1, "name": "sale"}
    assert len(created) == 1
    assert "idempotent-replay" not in first.headers
    assert second.headers["idempotent-replay"] == "true"


def test_requests_without_a_key_are_never_deduplicated() -> None:
    app, _, created = make_app()
    client = TestClient(app)

    post(client, key=None)
    post(client, key=None)

    assert len(created) == 2


def test_different_keys_are_independent() -> None:
    app, _, created = make_app()
    client = TestClient(app)

    post(client, key="a")
    post(client, key="b")

    assert len(created) == 2


def test_the_same_key_with_a_different_body_is_rejected_not_replayed() -> None:
    app, _, created = make_app()
    client = TestClient(app)
    post(client, name="first")

    reused = post(client, name="something else")

    assert reused.status_code == 422
    assert reused.json()["error_code"] == "idempotency_key_reused"
    assert len(created) == 1


def test_a_failed_request_is_not_stored_so_the_corrected_retry_goes_through() -> None:
    app, store, created = make_app()
    client = TestClient(app)

    failed = post(client, fail=True)
    assert failed.status_code == 422
    assert store.rows == {}

    retry = post(client, fail=False)
    assert retry.status_code == 201
    assert len(created) == 1


def test_keys_do_not_leak_between_callers() -> None:
    app, _, created = make_app()
    client = TestClient(app)

    mine = post(client, token="Bearer alice")
    theirs = post(client, token="Bearer bob")

    assert len(created) == 2
    assert mine.json()["id"] != theirs.json()["id"]


def test_an_over_long_key_is_rejected() -> None:
    app, _, created = make_app()

    response = post(TestClient(app), key="x" * 101)

    assert response.status_code == 422
    assert response.json()["error_code"] == "invalid_idempotency_key"
    assert created == []


def test_only_business_scoped_posts_are_considered() -> None:
    app, _, created = make_app()
    client = TestClient(app)

    client.post("/api/v1/other", headers={"Idempotency-Key": "k1", "Authorization": "Bearer a"})
    client.post("/api/v1/other", headers={"Idempotency-Key": "k1", "Authorization": "Bearer a"})

    assert len(created) == 2


def test_a_body_too_large_to_fingerprint_still_reaches_the_handler_intact() -> None:
    app, _, created = make_app()
    client = TestClient(app)
    big = "x" * (1024 * 1024 + 10)

    response = post(client, name=big)

    assert response.status_code == 201
    assert created[0]["name"] == big


@pytest.mark.anyio
async def test_concurrent_duplicates_create_one_record_and_the_rest_are_told_to_wait() -> None:
    app, _, created = make_app(delay=0.2)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        async def submit() -> httpx.Response:
            return await client.post(
                URL, headers={"Authorization": "Bearer a", "Idempotency-Key": "dbl"}, json={"name": "x"}
            )

        responses = await asyncio.gather(*(submit() for _ in range(5)))
        after = await submit()

    statuses = sorted(r.status_code for r in responses)
    assert statuses == [201, 409, 409, 409, 409]
    assert len(created) == 1
    assert after.status_code == 201 and after.headers["idempotent-replay"] == "true"


def test_keys_are_pruned_after_a_day() -> None:
    assert _KEEP_HOURS == 24


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
