from app.shared.domain.exceptions import ConflictException, NotFoundException, ValidationException


class VendorNotFoundException(NotFoundException):
    error_code = "vendor_not_found"


class VendorMissingW9Exception(ValidationException):
    error_code = "vendor_missing_w9"


class VendorAlreadyActiveException(ConflictException):
    error_code = "vendor_already_active"


class VendorInactiveException(ConflictException):
    """Raised when an operation (e.g. issuing a PO or invoice) targets a
    vendor that has been deactivated.
    """

    error_code = "vendor_inactive"
