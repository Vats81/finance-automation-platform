from app.shared.domain.exceptions import ConflictException, NotFoundException, ValidationException


class ExpenseNotFoundException(NotFoundException):
    error_code = "expense_not_found"


class ExpenseAlreadyVoidException(ConflictException):
    error_code = "expense_already_void"


class UnsupportedReceiptFileTypeException(ValidationException):
    error_code = "unsupported_receipt_file_type"


class ReceiptFileTooLargeException(ValidationException):
    error_code = "receipt_file_too_large"
