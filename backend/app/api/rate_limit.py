from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config.settings import get_settings

settings = get_settings()

# Shared limiter instance. Routers import this directly and apply
# `@limiter.limit(settings.rate_limit_write)` to individual write endpoints
# (see e.g. vendors/api/routes.py); reads fall back to `default_limits` below.
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default])


def register_rate_limiting(app: FastAPI) -> None:
    app.state.limiter = limiter
    # slowapi's handler is typed against its own narrower signature than
    # Starlette's generic exception-handler type, which mypy flags but
    # doesn't reflect an actual bug — this is slowapi's documented
    # integration pattern.
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
