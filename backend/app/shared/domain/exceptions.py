"""Domain exception hierarchy.

Every bounded context's domain exceptions subclass one of these four so that
`app/api/exception_handlers.py` can map them to RFC 7807 problem+json
responses generically, without importing anything from a specific context.
"""


class DomainException(Exception):
    """Base for all domain-layer errors. Carries a stable machine-readable code."""

    error_code: str = "domain_error"
    http_status: int = 400

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundException(DomainException):
    error_code = "not_found"
    http_status = 404


class ValidationException(DomainException):
    error_code = "validation_error"
    http_status = 422


class ConflictException(DomainException):
    error_code = "conflict"
    http_status = 409


class UnauthorizedDomainActionException(DomainException):
    """Raised when an actor lacks permission to perform a domain action.

    Distinct from the HTTP-layer 401/403 concerns in identity/api — this is
    the domain-level defense-in-depth check (e.g. inside ApprovalStep.approve()),
    so it still fires for non-HTTP callers such as Celery tasks.
    """

    error_code = "unauthorized_action"
    http_status = 403
