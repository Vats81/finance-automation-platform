from app.shared.domain.exceptions import ConflictException, NotFoundException, ValidationException


class SaleNotFoundException(NotFoundException):
    error_code = "sale_not_found"


class EmptySaleException(ValidationException):
    error_code = "empty_sale"


class PaymentExceedsOutstandingException(ValidationException):
    error_code = "payment_exceeds_outstanding"


class DuplicateInvoiceNumberException(ConflictException):
    error_code = "duplicate_invoice_number"


class SaleAlreadyVoidException(ConflictException):
    error_code = "sale_already_void"
