from app.shared.domain.exceptions import (
    ConflictException,
    DomainException,
    NotFoundException,
    ValidationException,
)


class UserNotFoundException(NotFoundException):
    error_code = "user_not_found"


class InvalidRoleAssignmentException(ValidationException):
    error_code = "invalid_role_assignment"


class InvalidTokenException(DomainException):
    """Bearer token failed signature/claims validation. 401, not 403 —
    the caller has no valid identity at all, as opposed to a valid identity
    lacking permission (UnauthorizedDomainActionException).
    """

    error_code = "invalid_token"
    http_status = 401


class UserDeactivatedException(DomainException):
    error_code = "user_deactivated"
    http_status = 403


class EmailAlreadyRegisteredException(ConflictException):
    error_code = "email_already_registered"


class InvalidCredentialsException(DomainException):
    """Wrong email/password, or a non-LOCAL account attempting local login.
    401 (no valid identity), and deliberately generic — never reveals which
    of email/password/account-type was wrong.
    """

    error_code = "invalid_credentials"
    http_status = 401


class EmailNotVerifiedException(DomainException):
    error_code = "email_not_verified"
    http_status = 403


class InvalidOrExpiredTokenException(ValidationException):
    """Email-verification or password-reset token is missing, expired, or
    doesn't match — distinct from InvalidTokenException, which is about the
    bearer auth token, not a one-time link token.
    """

    error_code = "invalid_or_expired_token"


class CannotDeactivateSelfException(ValidationException):
    """An admin can never deactivate their own account through the Admin
    Panel — it would immediately lock them out, since the admin flag lives
    on the User, not tied to any business.
    """

    error_code = "cannot_deactivate_self"
