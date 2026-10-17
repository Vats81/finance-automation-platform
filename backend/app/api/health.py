import os

import redis.asyncio as redis
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.container import get_db_session
from app.config.settings import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Liveness/readiness probe. Postgres is always critical: if it can't be
    reached the API can't serve anything, so that is 503 "unhealthy". Redis
    only counts when settings.redis_required is set; otherwise a Redis
    failure is reported as "degraded" with HTTP 200. This deployment doesn't
    run Redis, and returning 503 for that made the endpoint look like a
    permanent outage to any uptime monitor or load balancer. Each check's
    own result is always in `checks`, so a degraded Redis is still visible.
    """
    checks: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001 - health check must not raise
        # Include the exception type: the message alone can be ambiguous
        # (a bare "SSL/TLS required" looks the same whichever layer said it).
        checks["postgres"] = f"error: {type(exc).__name__}: {exc}"

    try:
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.aclose()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001 - health check must not raise
        checks["redis"] = f"error: {exc}"

    postgres_ok = checks["postgres"] == "ok"
    redis_ok = checks["redis"] == "ok"

    if not postgres_ok or (settings.redis_required and not redis_ok):
        status, status_code = "unhealthy", 503
    elif not redis_ok:
        status, status_code = "degraded", 200
    else:
        status, status_code = "healthy", 200

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "checks": checks,
            # Which build is actually running, and what TLS setting this
            # process actually read. When a config change "doesn't work",
            # these say whether the new build is live and whether it saw the
            # new value, instead of guessing. Neither is sensitive.
            "build": {
                "commit": os.environ.get("RENDER_GIT_COMMIT", "unknown")[:7],
                "database_ssl": getattr(settings, "database_ssl", "") or "(driver default)",
            },
        },
    )
