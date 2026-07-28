import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Structured (JSON-in-prod-shape) logging via structlog.

    Every log line carries a `correlation_id` when bound by
    app/api/middleware.py's CorrelationIdMiddleware, making it possible to
    trace a single request across the API and any Celery tasks it enqueues
    (the correlation id is passed through task kwargs).
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
