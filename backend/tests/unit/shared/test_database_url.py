import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from app.config.database_url import normalize_database_urls
from app.config.settings import Settings

_NEON = (
    "postgresql://app_user:pw@ep-cool-123.us-west-2.aws.neon.tech/neondb"
    "?sslmode=require&channel_binding=require"
)


def test_a_provider_url_is_split_into_clean_asyncpg_and_psycopg2_forms() -> None:
    async_url, sync_url = normalize_database_urls(_NEON)

    # asyncpg rejects `sslmode` and `channel_binding` as unknown arguments,
    # so it must get `ssl` and nothing else.
    assert async_url == (
        "postgresql+asyncpg://app_user:pw@ep-cool-123.us-west-2.aws.neon.tech/neondb?ssl=require"
    )
    assert sync_url == (
        "postgresql+psycopg2://app_user:pw@ep-cool-123.us-west-2.aws.neon.tech/neondb?sslmode=require"
    )


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+asyncpg", "postgresql+psycopg2"])
def test_any_postgres_scheme_spelling_is_accepted(scheme: str) -> None:
    async_url, sync_url = normalize_database_urls(f"{scheme}://u:p@db.example.com:5432/app")

    assert async_url == "postgresql+asyncpg://u:p@db.example.com:5432/app"
    assert sync_url == "postgresql+psycopg2://u:p@db.example.com:5432/app"


def test_asyncpg_style_ssl_is_translated_for_psycopg2() -> None:
    _, sync_url = normalize_database_urls("postgresql+asyncpg://u:p@h/db?ssl=require")

    assert sync_url == "postgresql+psycopg2://u:p@h/db?sslmode=require"


def test_other_query_parameters_are_kept() -> None:
    async_url, sync_url = normalize_database_urls("postgresql://u:p@h/db?sslmode=require&application_name=fap")

    assert "application_name=fap" in async_url and "application_name=fap" in sync_url


def test_a_password_with_special_characters_survives() -> None:
    raw = "postgresql://user:p%40ss%2Fw%3Ard%23@h/db?sslmode=require"

    for normalized in normalize_database_urls(raw):
        assert make_url(normalized).password == "p@ss/w:rd#"


def test_the_local_development_default_is_unchanged() -> None:
    local = "postgresql+asyncpg://fap_user:fap_dev_password@localhost:5432/fap_db"

    assert normalize_database_urls(local)[0] == local


def test_non_postgres_urls_pass_through_untouched() -> None:
    assert normalize_database_urls("sqlite+aiosqlite:///x.db") == (
        "sqlite+aiosqlite:///x.db",
        "sqlite+aiosqlite:///x.db",
    )


def test_garbage_raises_instead_of_being_silently_accepted() -> None:
    with pytest.raises(ArgumentError):
        normalize_database_urls("not a url at all")


# --- through Settings (what the running app actually reads) -------------------


def test_settings_needs_only_one_url_and_derives_the_sync_one() -> None:
    settings = Settings(DATABASE_URL=_NEON)

    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.database_url_sync == (
        "postgresql+psycopg2://app_user:pw@ep-cool-123.us-west-2.aws.neon.tech/neondb?sslmode=require"
    )


def test_an_explicit_sync_url_is_respected_and_normalized() -> None:
    settings = Settings(DATABASE_URL=_NEON, DATABASE_URL_SYNC="postgresql://other:pw@elsewhere/db?sslmode=require")

    assert settings.database_url_sync == "postgresql+psycopg2://other:pw@elsewhere/db?sslmode=require"


def test_neon_hosts_get_tls_automatically_even_with_a_bare_url() -> None:
    settings = Settings(DATABASE_URL="postgresql://u:p@ep-cool-123.us-west-2.aws.neon.tech/neondb")

    assert settings.effective_database_ssl == "require"


def test_an_unparseable_url_does_not_crash_settings() -> None:
    assert Settings(DATABASE_URL="not a url at all").database_url == "not a url at all"
