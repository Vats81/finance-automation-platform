"""With REGISTRATION_REQUIRES_INVITE on, only invited emails can create an account."""

import dataclasses
import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.rate_limit import limiter
from app.beta_waitlist.api.routes import get_waitlist_store
from app.beta_waitlist.domain.status import WaitlistStatus
from app.bootstrap.app_factory import create_app
from app.bootstrap.container import get_uow
from app.config.settings import get_settings
from tests.fakes.fake_unit_of_work import FakeUnitOfWork
from tests.unit.beta_waitlist.test_beta_waitlist import MemoryStore

BODY = {"email": "asha@example.com", "password": "Sup3rSecret!pw", "display_name": "Asha"}


@pytest.fixture
def signup(monkeypatch: pytest.MonkeyPatch):
    limiter.enabled = False
    monkeypatch.setenv("REGISTRATION_REQUIRES_INVITE", "true")
    get_settings.cache_clear()
    # auth_routes read the settings object at import time, so patch the live instance too.
    from app.identity.api import auth_routes

    monkeypatch.setattr(auth_routes, "settings", get_settings())
    store, uow = MemoryStore(), FakeUnitOfWork()
    app = create_app()
    app.dependency_overrides[get_waitlist_store] = lambda: store
    app.dependency_overrides[get_uow] = lambda: uow
    yield TestClient(app, raise_server_exceptions=False), store, uow
    limiter.enabled = True
    get_settings.cache_clear()


async def _add(store: MemoryStore, email: str, status: WaitlistStatus) -> uuid.UUID:
    entry = await store.upsert_interest(
        name="Asha",
        work_email=email,
        business_name=None,
        business_type=None,
        bookkeeping_method=None,
        reporting_problem=None,
        weekly_feedback_ok=True,
    )
    store.rows[entry.id] = dataclasses.replace(entry, status=status)
    return entry.id


def test_someone_who_is_not_on_the_list_cannot_sign_up(signup) -> None:  # type: ignore[no-untyped-def]
    client, _, _ = signup

    response = client.post("/api/v1/auth/register", json=BODY)

    assert response.status_code == 403
    assert response.json()["error_code"] == "registration_invite_required"
    assert "invitation" in response.json()["detail"]


@pytest.mark.parametrize(
    "status",
    [
        WaitlistStatus.INTERESTED,
        WaitlistStatus.QUALIFIED,
        WaitlistStatus.WAITING_FOR_CHECKS,
        WaitlistStatus.PAUSED,
    ],
)
async def test_registering_interest_or_being_qualified_is_not_an_invitation(signup, status) -> None:  # type: ignore[no-untyped-def]
    client, store, _ = signup
    await _add(store, "asha@example.com", status)

    assert client.post("/api/v1/auth/register", json=BODY).status_code == 403


async def test_an_invited_person_can_sign_up_and_becomes_onboarded(signup) -> None:  # type: ignore[no-untyped-def]
    client, store, _ = signup
    entry_id = await _add(store, "Asha@Example.com", WaitlistStatus.INVITED)

    response = client.post("/api/v1/auth/register", json=BODY)

    assert response.status_code == 201
    assert store.rows[entry_id].status == WaitlistStatus.ONBOARDED


async def test_an_onboarded_person_is_still_recognised_but_cannot_register_twice(signup) -> None:  # type: ignore[no-untyped-def]
    client, store, _ = signup
    await _add(store, "asha@example.com", WaitlistStatus.INVITED)
    assert client.post("/api/v1/auth/register", json=BODY).status_code == 201

    assert client.post("/api/v1/auth/register", json=BODY).status_code == 409


def test_an_uninvited_address_learns_nothing_about_who_is_registered(signup) -> None:  # type: ignore[no-untyped-def]
    client, _, uow = signup

    first = client.post("/api/v1/auth/register", json=BODY)
    second = client.post("/api/v1/auth/register", json={**BODY, "email": "someone.else@example.com"})

    assert first.status_code == second.status_code == 403
    assert first.json()["detail"] == second.json()["detail"]


def test_with_the_switch_off_signup_stays_open(monkeypatch: pytest.MonkeyPatch) -> None:
    limiter.enabled = False
    monkeypatch.delenv("REGISTRATION_REQUIRES_INVITE", raising=False)
    get_settings.cache_clear()
    from app.identity.api import auth_routes

    monkeypatch.setattr(auth_routes, "settings", get_settings())
    app = create_app()
    app.dependency_overrides[get_waitlist_store] = lambda: MemoryStore()
    app.dependency_overrides[get_uow] = lambda: FakeUnitOfWork()

    response = TestClient(app, raise_server_exceptions=False).post("/api/v1/auth/register", json=BODY)

    assert response.status_code == 201
    limiter.enabled = True
    get_settings.cache_clear()
