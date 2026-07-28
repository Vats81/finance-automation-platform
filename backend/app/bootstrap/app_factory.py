from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import register_exception_handlers
from app.api.health import router as health_router
from app.api.main_router import api_router
from app.api.middleware import CorrelationIdMiddleware
from app.api.openapi import custom_openapi
from app.api.rate_limit import register_rate_limiting
from app.bootstrap.lifespan import lifespan
from app.config.settings import get_settings
from app.shared.infrastructure.logging import configure_logging
from app.shared.infrastructure.tracing import configure_tracing


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Finance Automation Platform API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIdMiddleware)

    register_exception_handlers(app)
    register_rate_limiting(app)

    app.include_router(health_router)
    app.include_router(api_router)

    # Documented FastAPI pattern for a custom OpenAPI schema; mypy flags
    # reassigning a bound method, but this is how FastAPI itself expects it.
    app.openapi = lambda: custom_openapi(app)  # type: ignore[method-assign]

    if settings.otel_exporter == "console":
        configure_tracing(app, settings.otel_service_name)

    return app
