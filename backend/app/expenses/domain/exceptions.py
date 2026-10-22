from app.shared.domain.exceptions import (
    ConflictException,
    DomainException,
    NotFoundException,
    ValidationException,
)


class ExpenseNotFoundException(NotFoundException):
    error_code = "expense_not_found"


class ExpenseAlreadyVoidException(ConflictException):
    error_code = "expense_already_void"


class UnsupportedReceiptFileTypeException(ValidationException):
    error_code = "unsupported_receipt_file_type"


class ReceiptScannerUnavailableException(DomainException):
    """The AI provider failed or kept returning nothing usable. Not the user's
    fault, and nothing was saved: they can retry or enter the bill by hand.
    """

    error_code = "receipt_scanner_unavailable"
    http_status = 503


class UnreadableReceiptPdfException(ValidationException):
    error_code = "unreadable_receipt_pdf"


class ReceiptFileTooLargeException(ValidationException):
    error_code = "receipt_file_too_large"
