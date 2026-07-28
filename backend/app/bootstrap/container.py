"""Composition root.

This is the ONLY module in the codebase allowed to wire concrete
infrastructure adapters to the abstract ports/interfaces the domain and
application layers depend on (SOLID's Dependency Inversion Principle in
practice). Everything else — use cases, routers, Celery tasks — receives
its dependencies through FastAPI's `Depends(...)` (API layer) or explicit
constructor injection (Celery task bodies), never by importing an adapter
directly.

Providers: `get_uow` (per-request AppUnitOfWork), `get_jwt_validator`
(Entra ID / dev-mode auth), `get_file_storage` (Azure Blob/Azurite),
`get_task_queue` (Celery), and `get_event_bus` (in-process pub/sub feeding
the outbox relay — see workers/tasks/outbox_relay_task.py).
"""

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.bootstrap.event_handlers import register_all_event_handlers
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.config.settings import Settings, get_settings
from app.identity.infrastructure.entra.jwks_cache import JwksCache
from app.identity.infrastructure.entra.jwt_validator import EntraJwtValidator
from app.identity.infrastructure.local_auth.token_issuer import LocalTokenIssuer
from app.identity.infrastructure.local_auth.token_validator import LocalTokenValidator
from app.shared.application.ports import (
    IAiClient,
    IClock,
    IEmailSender,
    IFileStorage,
    IPasswordHasher,
    ITaskQueue,
    IWhatsAppSender,
)
from app.shared.infrastructure.ai_client import AnthropicAiClient, ConsoleAiClient
from app.shared.infrastructure.blob_storage import AzureBlobStorageAdapter
from app.shared.infrastructure.celery_task_queue import CeleryTaskQueueAdapter
from app.shared.infrastructure.clock import SystemClock
from app.shared.infrastructure.db.session import create_engine, create_session_factory
from app.shared.infrastructure.email_sender import ConsoleEmailSender, SmtpEmailSender
from app.shared.infrastructure.event_bus import InProcessEventBus
from app.shared.infrastructure.password_hasher import BcryptPasswordHasher
from app.shared.infrastructure.whatsapp_sender import ConsoleWhatsAppSender, TwilioWhatsAppSender


class Container:
    """Lightweight composition root. Deliberately not framework-heavy
    dependency-injector wiring for request-scoped objects (a session/UoW
    must be created fresh per request) — those are exposed as FastAPI
    dependency functions below instead, which is the idiomatic FastAPI
    pattern and keeps the dependency graph explicit and easy to trace.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine: AsyncEngine = create_engine()
        self.session_factory: async_sessionmaker[AsyncSession] = create_session_factory(self.engine)

    async def dispose(self) -> None:
        await self.engine.dispose()


@lru_cache
def get_container() -> Container:
    return Container(get_settings())


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    container = get_container()
    async with container.session_factory() as session:
        yield session


async def get_uow() -> AsyncGenerator[AppUnitOfWork, None]:
    container = get_container()
    async with container.session_factory() as session:
        yield AppUnitOfWork(session)


@lru_cache
def get_jwt_validator() -> EntraJwtValidator:
    settings = get_settings()
    jwks_cache = JwksCache(settings.redis_url, settings.entra_jwks_uri)
    return EntraJwtValidator(settings, jwks_cache)


@lru_cache
def get_file_storage() -> IFileStorage:
    settings = get_settings()
    return AzureBlobStorageAdapter(settings.azure_storage_connection_string)


@lru_cache
def get_task_queue() -> ITaskQueue:
    # Imported lazily to avoid the API process eagerly importing worker-only
    # task modules pulled in transitively by app.workers.celery_app.
    from app.workers.celery_app import celery_app

    return CeleryTaskQueueAdapter(celery_app)


@lru_cache
def get_event_bus() -> InProcessEventBus:
    bus = InProcessEventBus()
    register_all_event_handlers(bus)
    return bus


@lru_cache
def get_password_hasher() -> IPasswordHasher:
    return BcryptPasswordHasher()


@lru_cache
def get_clock() -> IClock:
    return SystemClock()


@lru_cache
def get_local_token_issuer() -> LocalTokenIssuer:
    return LocalTokenIssuer(get_settings())


@lru_cache
def get_local_token_validator() -> LocalTokenValidator:
    return LocalTokenValidator(get_settings())


@lru_cache
def get_email_sender() -> IEmailSender:
    settings = get_settings()
    if settings.smtp_configured:
        return SmtpEmailSender(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            from_address=settings.smtp_from_address,
        )
    return ConsoleEmailSender()


@lru_cache
def get_whatsapp_sender() -> IWhatsAppSender:
    settings = get_settings()
    if settings.whatsapp_provider == "twilio":
        return TwilioWhatsAppSender(
            account_sid=settings.twilio_account_sid,
            auth_token=settings.twilio_auth_token,
            from_number=settings.twilio_whatsapp_from,
        )
    return ConsoleWhatsAppSender()


@lru_cache
def get_ai_client() -> IAiClient:
    settings = get_settings()
    if settings.ai_provider == "anthropic":
        return AnthropicAiClient(api_key=settings.anthropic_api_key, model=settings.anthropic_model)
    return ConsoleAiClient()
