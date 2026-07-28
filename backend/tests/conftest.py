"""Shared pytest fixtures.

Unit tests (tests/unit/) don't use any fixture here — they exercise pure
domain/application logic with tests/fakes/. Integration tests (tests/integration/,
marked `@pytest.mark.integration`) use the Postgres-testcontainer fixtures
below, which require a running Docker daemon; they're skipped automatically
if Docker isn't reachable (see `docker_available`).
"""

import base64
import json
import subprocess
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.approvals.infrastructure import models as approvals_models  # noqa: F401
from app.audit.infrastructure import models as audit_models  # noqa: F401
from app.identity.infrastructure import models as identity_models  # noqa: F401
from app.invoices.infrastructure import models as invoices_models  # noqa: F401
from app.payments.infrastructure import models as payments_models  # noqa: F401
from app.purchase_orders.infrastructure import models as purchase_orders_models  # noqa: F401
from app.shared.infrastructure.db.base import Base

# Import every context's ORM models so Base.metadata is fully populated
# before create_all — mirrors alembic/env.py's import list.
from app.shared.infrastructure.outbox import outbox_model  # noqa: F401
from app.vendors.infrastructure import models as vendors_models  # noqa: F401


def _docker_available() -> bool:
    try:
        subprocess.run(["docker", "info"], capture_output=True, timeout=5, check=True)
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def docker_available() -> bool:
    return _docker_available()


@pytest.fixture(scope="session")
def postgres_container(docker_available: bool):
    if not docker_available:
        pytest.skip("Docker is not available in this environment")

    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as container:
        yield container


@pytest_asyncio.fixture(scope="session")
async def engine(postgres_container) -> AsyncGenerator[AsyncEngine, None]:
    url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
    test_engine = create_async_engine(url)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """One savepoint-nested transaction per test, rolled back on teardown —
    every test sees a clean database without recreating the schema each time.
    """
    connection = await engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    session = session_factory()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Real FastAPI app, with only `get_uow` overridden to run inside the
    test's rollback-per-test transaction — every other dependency
    (auth, rate limiting, exception handling) runs exactly as in production.
    """
    from app.bootstrap.app_factory import create_app
    from app.bootstrap.container import get_uow
    from app.bootstrap.unit_of_work import AppUnitOfWork

    app = create_app()

    async def override_get_uow() -> AsyncGenerator[AppUnitOfWork, None]:
        yield AppUnitOfWork(db_session)

    app.dependency_overrides[get_uow] = override_get_uow

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client

    app.dependency_overrides.clear()


def make_dev_token(*, oid: str = "test-oid", email: str = "test@example.com", name: str = "Test User") -> str:
    """Mirrors the frontend's dev-mode token format — see
    identity/infrastructure/entra/jwt_validator.py._validate_dev_token.
    """
    payload = {"oid": oid, "email": email, "name": name}
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"dev.{encoded}"


def auth_header(**claims: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_dev_token(**claims)}"}
