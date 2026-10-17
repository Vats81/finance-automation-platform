"""/health's status mapping. Postgres is always critical; Redis only
matters when settings.redis_required is set. Before this, a missing Redis
(never deployed here) made the endpoint return 503 permanently, which any
uptime monitor reads as the service being down.
"""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import health as health_module
from app.api.health import router
from app.bootstrap.container import get_db_session
from app.config.settings import get_settings


class _Session:
    def __init__(self, ok: bool) -> None:
        self._ok = ok

    async def execute(self, *_args, **_kwargs) -> None:
        if not self._ok:
            raise ConnectionError("connection refused")


class _Redis:
    def __init__(self, ok: bool) -> None:
        self._ok = ok

    async def ping(self) -> None:
        if not self._ok:
            raise ConnectionError("redis down")

    async def aclose(self) -> None:
        return None


def _client(
    monkeypatch: pytest.MonkeyPatch, *, postgres_ok: bool, redis_ok: bool, redis_required: bool
) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db_session] = lambda: _Session(postgres_ok)
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(
        redis_url="redis://x",
        redis_required=redis_required,
        database_ssl="",
        effective_database_ssl="require",
    )
    monkeypatch.setattr(health_module.redis, "from_url", lambda _url: _Redis(redis_ok))
    return TestClient(app)


def test_everything_up_is_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _client(monkeypatch, postgres_ok=True, redis_ok=True, redis_required=False).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_redis_down_but_not_required_is_degraded_not_an_outage(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _client(monkeypatch, postgres_ok=True, redis_ok=False, redis_required=False).get("/health")

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "degraded"
    # Still visible, just not fatal.
    assert body["checks"]["redis"].startswith("error:")
    assert body["checks"]["postgres"] == "ok"


def test_redis_down_and_required_is_unhealthy(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _client(monkeypatch, postgres_ok=True, redis_ok=False, redis_required=True).get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"


@pytest.mark.parametrize("redis_required", [False, True])
def test_postgres_down_is_always_unhealthy_and_says_why(
    monkeypatch: pytest.MonkeyPatch, redis_required: bool
) -> None:
    response = _client(
        monkeypatch, postgres_ok=False, redis_ok=True, redis_required=redis_required
    ).get("/health")

    body = response.json()
    assert response.status_code == 503
    assert body["status"] == "unhealthy"
    assert "connection refused" in body["checks"]["postgres"]


def test_reports_the_running_commit_and_the_tls_setting_it_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENDER_GIT_COMMIT", "3e2c3fcabcdef1234567890")

    body = _client(monkeypatch, postgres_ok=True, redis_ok=True, redis_required=False).get("/health").json()

    build = body["build"]
    assert build["commit"] == "3e2c3fc"
    assert build["database_ssl"] == "(not set)"
    assert build["database_ssl_effective"] == "require"
    assert build["started_at"]  # ISO timestamp of process start


def test_postgres_error_names_the_exception_type(monkeypatch: pytest.MonkeyPatch) -> None:
    body = _client(monkeypatch, postgres_ok=False, redis_ok=True, redis_required=False).get("/health").json()

    assert body["checks"]["postgres"].startswith("error: ConnectionError: ")

