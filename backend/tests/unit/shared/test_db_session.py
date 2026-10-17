from app.shared.infrastructure.db.session import build_connect_args


def test_default_leaves_tls_to_the_driver() -> None:
    # Blank DATABASE_SSL must not add an `ssl` argument — local Postgres
    # and CI don't speak TLS and must keep working.
    assert build_connect_args("") == {"timeout": 10}


def test_database_ssl_is_passed_to_asyncpg_as_ssl() -> None:
    assert build_connect_args("require") == {"timeout": 10, "ssl": "require"}
