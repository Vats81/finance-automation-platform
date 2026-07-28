import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)

CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assigns (or propagates) a correlation id per request, binds it into
    structlog's contextvars so every log line in the request's lifecycle
    carries it, and echoes it back in the response header.

    Background work in this platform is always triggered via the
    transactional outbox (see shared/infrastructure/outbox/), not enqueued
    synchronously mid-request, so a request's correlation id doesn't extend
    into the worker's processing of it — by the time the outbox relay picks
    an event up, it's a distinct async unit of work. Worker-side logs
    correlate by aggregate_id/event_id instead (see
    workers/tasks/outbox_relay_task.py).
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER, str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers[CORRELATION_ID_HEADER] = correlation_id
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response
