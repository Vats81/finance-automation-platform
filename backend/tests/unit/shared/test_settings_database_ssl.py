import pytest

from app.config.settings import Settings


def _ssl(url: str, explicit: str = "") -> str:
    # Settings fields are alias-only, so overrides use the env-var names.
    return Settings(DATABASE_URL=url, DATABASE_SSL=explicit).effective_database_ssl


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+asyncpg://u:p@dpg-abc123xyz-a.oregon-postgres.render.com/fap_db",  # external
        "postgresql+asyncpg://u:p@something.render.com:5432/fap_db",
    ],
)
def test_render_external_hosts_get_tls_automatically(url: str) -> None:
    assert _ssl(url) == "require"


@pytest.mark.parametrize(
    "url",
    [
        # Render's short internal name: reached over the private network, not
        # the TLS-terminating external proxy, so it keeps the driver default.
        "postgresql+asyncpg://u:p@dpg-abc123xyz-a/fap_db",
        "postgresql+asyncpg://u:p@localhost:5432/db",
        "postgresql+asyncpg://u:p@127.0.0.1:5432/db",
        "postgresql+asyncpg://u:p@postgres:5432/db",  # docker-compose service name
        "postgresql+asyncpg://u:p@db.example.com:5432/db",
    ],
)
def test_other_hosts_keep_the_driver_default(url: str) -> None:
    # Local dev and CI Postgres don't speak TLS and must keep working.
    assert _ssl(url) == ""


def test_explicit_setting_always_wins_even_on_render_hosts() -> None:
    render_url = "postgresql+asyncpg://u:p@dpg-abc-a.oregon-postgres.render.com/db"

    assert _ssl(render_url, "disable") == "disable"
    assert _ssl("postgresql+asyncpg://u:p@localhost/db", "require") == "require"


def test_an_unparseable_url_does_not_crash_settings() -> None:
    assert _ssl("not a url at all") == ""
