from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import seed as seed_module
from app.bootstrap.container import get_clock, get_password_hasher
from app.config.settings import get_settings
from app.shared.application.seed_demo_data import DEMO_USERS, build_credentials

_REPO_ROOT = Path(__file__).resolve().parents[4]


def test_without_configuration_every_account_gets_its_own_random_password() -> None:
    credentials = build_credentials()

    assert set(credentials) == set(DEMO_USERS)
    assert len(set(credentials.values())) == len(DEMO_USERS)  # all distinct
    assert all(len(password) >= 14 for password in credentials.values())
    # Not reproducible: a second call yields different passwords.
    assert build_credentials() != credentials


def test_configured_passwords_are_used_by_kind() -> None:
    credentials = build_credentials(admin_password="the-admin-pw", user_password="the-friend-pw")

    assert credentials["admin@financeai.app"] == "the-admin-pw"
    friends = {e: p for e, p in credentials.items() if e != "admin@financeai.app"}
    assert set(friends.values()) == {"the-friend-pw"}


def test_only_the_unset_kind_falls_back_to_random() -> None:
    credentials = build_credentials(admin_password="the-admin-pw")

    assert credentials["admin@financeai.app"] == "the-admin-pw"
    assert credentials["friend1@financeai-test.app"] != credentials["friend2@financeai-test.app"]


@pytest.mark.parametrize("path", ["backend/app/shared/application/seed_demo_data.py", "DEPLOY.md"])
def test_the_old_publicly_known_passwords_never_come_back(path: str) -> None:
    # These were hardcoded in this public repo for accounts that exist on the
    # live deployment, one of them the platform admin.
    text = (_REPO_ROOT / path).read_text(encoding="utf-8")

    for known in ("Admin@FinanceAI2026!", "Friend1@Test2026!", "Friend5@Test2026!"):
        assert known not in text, f"{known} reappeared in {path}"


# --- the endpoint -------------------------------------------------------------


@pytest.fixture
def seed_client(monkeypatch: pytest.MonkeyPatch):
    calls: list[dict] = []

    async def fake_run_seed(session_factory, hasher, clock, **kwargs) -> dict[str, object]:
        calls.append(kwargs)
        return {
            "created": ["admin@financeai.app"],
            "skipped": [],
            "credentials": {"admin@financeai.app": "x"},
        }

    monkeypatch.setattr(seed_module, "run_seed", fake_run_seed)
    monkeypatch.setattr(seed_module, "get_container", lambda: SimpleNamespace(session_factory=object()))

    def make(seed_secret: str, admin_pw: str = "", user_pw: str = "") -> TestClient:
        app = FastAPI()
        app.include_router(seed_module.router)
        app.dependency_overrides[get_settings] = lambda: SimpleNamespace(
            seed_secret=seed_secret, seed_admin_password=admin_pw, seed_user_password=user_pw
        )
        app.dependency_overrides[get_password_hasher] = lambda: object()
        app.dependency_overrides[get_clock] = lambda: object()
        return TestClient(app)

    return make, calls


def test_the_endpoint_is_disabled_when_no_secret_is_configured(seed_client) -> None:
    make, calls = seed_client

    assert make("").get("/internal/seed-demo-users", params={"secret": ""}).status_code == 403
    assert calls == []


def test_a_wrong_secret_is_rejected(seed_client) -> None:
    make, calls = seed_client

    assert make("right").get("/internal/seed-demo-users", params={"secret": "wrong"}).status_code == 403
    assert calls == []


def test_the_right_secret_seeds_passes_configured_passwords_and_returns_credentials(seed_client) -> None:
    make, calls = seed_client

    response = make("right", admin_pw="adm", user_pw="usr").get(
        "/internal/seed-demo-users", params={"secret": "right"}
    )

    assert response.status_code == 200
    assert response.json()["credentials"] == {"admin@financeai.app": "x"}
    assert calls == [{"admin_password": "adm", "user_password": "usr"}]
