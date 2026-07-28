from app.shared.domain.exceptions import ConflictException, NotFoundException, ValidationException


class InvoiceNotFoundException(NotFoundException):
    error_code = "invoice_not_found"


class EmptyInvoiceException(ValidationException):
    error_code = "empty_invoice"


class InvalidInvoiceStateTransitionException(ConflictException):
    error_code = "invalid_invoice_state_transition"
