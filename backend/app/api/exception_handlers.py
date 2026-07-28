import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.shared.domain.exceptions import DomainException

logger = logging.getLogger(__name__)

PROBLEM_CONTENT_TYPE = "application/problem+json"


def _problem_response(
    *, status_code: int, error_code: str, title: str, detail: str, instance: str, extra: dict | None = None
) -> JSONResponse:
    body = {
        "type": f"https://errors.finance-automation-platform.dev/{error_code}",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
        "error_code": error_code,
    }
    if extra:
        body.update(extra)
    return JSONResponse(status_code=status_code, content=body, media_type=PROBLEM_CONTENT_TYPE)


def register_exception_handlers(app: FastAPI) -> None:
    """Maps the DomainException hierarchy (and framework validation errors)
    to RFC 7807 problem+json responses. This is the ONLY place HTTP status
    codes are derived from domain errors — individual routers never catch
    DomainException themselves.
    """

    @app.exception_handler(DomainException)
    async def handle_domain_exception(request: Request, exc: DomainException) -> JSONResponse:
        return _problem_response(
            status_code=exc.http_status,
            error_code=exc.error_code,
            title=type(exc).__name__,
            detail=exc.message,
            instance=str(request.url.path),
            extra={"details": exc.details} if exc.details else None,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem_response(
            status_code=422,
            error_code="request_validation_error",
            title="Request Validation Error",
            detail="One or more fields failed validation.",
            instance=str(request.url.path),
            extra={"errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s", request.url.path)
        return _problem_response(
            status_code=500,
            error_code="internal_server_error",
            title="Internal Server Error",
            detail="An unexpected error occurred.",
            instance=str(request.url.path),
        )
