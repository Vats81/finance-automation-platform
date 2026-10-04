"""Route-level tests for the public POST /api/v1/contact endpoint. Builds a
minimal FastAPI app around just this router with the store and email
sender overridden, so it exercises the real request validation, honeypot,
and rate limiting without needing a database.
"""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.rate_limit import limiter, register_rate_limiting
from app.bootstrap.container import get_email_sender
from app.contact.api.dependencies import get_contact_request_store
from app.contact.api.routes import router
from tests.fakes.fake_ports import FakeEmailSender
from tests.unit.contact.test_submit_contact_request import InMemoryContactRequestStore

_VALID = {"name": "Asha Rao", "email": "asha@example.com", "business_name": "Rao Traders", "message": "Demo?"}


@pytest.fixture
def harness(monkeypatch: pytest.MonkeyPatch):
    limiter.reset()
    store = InMemoryContactRequestStore()
    sender = FakeEmailSender()
    app = FastAPI()
    register_rate_limiting(app)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_contact_request_store] = lambda: store
    app.dependency_overrides[get_email_sender] = lambda: sender
    monkeypatch.setattr(
        "app.contact.api.routes.get_settings",
        lambda: SimpleNamespace(contact_inbox_email="owner@example.com"),
    )
    return TestClient(app), store, sender


def test_valid_submission_is_saved_and_emailed(harness) -> None:
    client, store, sender = harness

    response = client.post("/api/v1/contact", json=_VALID)

    assert response.status_code == 201
    assert response.json() == {"received": True}
    assert len(store.rows) == 1
    assert len(sender.sent) == 1


def test_blank_optional_fields_are_stored_as_none(harness) -> None:
    client, store, _ = harness

    response = client.post(
        "/api/v1/contact",
        json={"name": "Asha", "email": "asha@example.com", "business_name": "  ", "message": ""},
    )

    assert response.status_code == 201
    row = next(iter(store.rows.values()))
    assert row.business_name is None
    assert row.message is None


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Asha", "email": "not-an-email"},
        {"name": "   ", "email": "asha@example.com"},
        {"email": "asha@example.com"},
        {"name": "Asha", "email": "asha@example.com", "message": "x" * 2001},
    ],
)
def test_invalid_submissions_are_rejected_and_not_saved(harness, payload: dict) -> None:
    client, store, sender = harness

    response = client.post("/api/v1/contact", json=payload)

    assert response.status_code == 422
    assert store.rows == {}
    assert sender.sent == []


def test_honeypot_hit_looks_successful_but_saves_nothing(harness) -> None:
    client, store, sender = harness

    response = client.post("/api/v1/contact", json={**_VALID, "website": "http://spam.example"})

    assert response.status_code == 201
    assert response.json() == {"received": True}
    assert store.rows == {}
    assert sender.sent == []


def test_endpoint_is_rate_limited(harness) -> None:
    client, store, _ = harness

    statuses = [client.post("/api/v1/contact", json=_VALID).status_code for _ in range(11)]

    assert statuses[:10] == [201] * 10
    assert statuses[10] == 429
    assert len(store.rows) == 10
