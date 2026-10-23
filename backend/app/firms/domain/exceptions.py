from app.shared.domain.exceptions import (
    ConflictException,
    NotFoundException,
    UnauthorizedDomainActionException,
    ValidationException,
)


class FirmNotFoundException(NotFoundException):
    error_code = "firm_not_found"


class NotAFirmMemberException(UnauthorizedDomainActionException):
    error_code = "not_a_firm_member"


class FirmSuspendedException(UnauthorizedDomainActionException):
    error_code = "firm_suspended"


class FirmStaffNotFoundException(NotFoundException):
    error_code = "firm_staff_not_found"


class FirmClientNotFoundException(NotFoundException):
    error_code = "firm_client_not_found"


class StaffInviteeNotRegisteredException(ValidationException):
    error_code = "staff_invitee_not_registered"


class StaffAlreadyMemberException(ConflictException):
    error_code = "staff_already_member"


class FirmOwnerRoleNotAssignableException(ValidationException):
    """The Owner role belongs to the person who created the firm; it cannot be
    granted by invite or role change.
    """

    error_code = "firm_owner_role_not_assignable"


class CannotModifyFirmOwnerException(ValidationException):
    error_code = "cannot_modify_firm_owner"


class CannotChangeOwnFirmRoleException(ValidationException):
    error_code = "cannot_change_own_firm_role"


class FirmStaffLimitExceededException(ConflictException):
    error_code = "firm_staff_limit_exceeded"


class ClientHasNoOtherOwnerException(ConflictException):
    """Releasing a client would leave the business with no one on the client's
    side, so the firm must first give the client's own owner access.
    """

    error_code = "client_has_no_other_owner"
