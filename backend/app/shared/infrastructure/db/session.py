from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import get_settings


def build_connect_args(database_ssl: str) -> dict[str, object]:
    # asyncpg's own default connect timeout is 60s — long enough that an
    # unreachable/deleted database (wrong host, expired free-tier instance,
    # ...) looks identical to a slow app from the outside for a full minute
    # per attempt. 10s is still generous for a real connection and fails
    # fast enough to show up clearly in logs.
    connect_args: dict[str, object] = {"timeout": 10}
    if database_ssl:
        # asyncpg's name for the libpq sslmode values (same strings).
        connect_args["ssl"] = database_ssl
    return connect_args


def create_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False,
        connect_args=build_connect_args(settings.database_ssl),
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session
