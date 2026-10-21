"""Turn a Postgres connection string, exactly as a hosting provider hands it
out, into the two forms this app needs: an asyncpg URL for the application
and a psycopg2 URL for Alembic migrations.

Providers give a plain `postgresql://user:pass@host/db?sslmode=require...`.
The app used to need the scheme hand-edited into two different spellings,
and the TLS parameter spelled differently for each driver (`sslmode` for
psycopg2, `ssl` for asyncpg, which rejects `sslmode` outright). Copying a
provider URL verbatim therefore failed in confusing ways, which is a real
cost when you want to move to a different database host. This accepts the
provider's string as-is.
"""

from sqlalchemy.engine import make_url

# Names the postgres URL scheme may arrive under (`postgres://` is what some
# providers emit; SQLAlchemy 2 doesn't recognise it as a dialect).
_POSTGRES_FAMILY = {"postgres", "postgresql"}


def normalize_database_urls(raw: str) -> tuple[str, str]:
    """Returns (asyncpg_url, psycopg2_url). Non-Postgres URLs are returned
    unchanged for both. Raises sqlalchemy.exc.ArgumentError if `raw` isn't a
    parseable URL.
    """
    url = make_url(raw)
    if url.drivername.split("+")[0] not in _POSTGRES_FAMILY:
        return raw, raw

    query = dict(url.query)
    # Either spelling means the same thing: which TLS mode to use.
    tls_mode = query.pop("ssl", None) or query.pop("sslmode", None)
    query.pop("sslmode", None)
    # libpq-only hardening option some providers append; asyncpg rejects it
    # as an unknown argument, so drop it rather than break the connection.
    query.pop("channel_binding", None)

    async_query = dict(query)
    sync_query = dict(query)
    if tls_mode:
        async_query["ssl"] = tls_mode
        sync_query["sslmode"] = tls_mode

    async_url = url.set(drivername="postgresql+asyncpg", query=async_query)
    sync_url = url.set(drivername="postgresql+psycopg2", query=sync_query)
    return (
        async_url.render_as_string(hide_password=False),
        sync_url.render_as_string(hide_password=False),
    )
