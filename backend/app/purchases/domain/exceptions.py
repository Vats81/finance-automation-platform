from app.shared.domain.exceptions import ConflictException, NotFoundException, ValidationException


class PurchaseNotFoundException(NotFoundException):
    error_code = "purchase_not_found"


class EmptyPurchaseException(ValidationException):
    error_code = "empty_purchase"


class PurchasePaymentExceedsOutstandingException(ValidationException):
    error_code = "purchase_payment_exceeds_outstanding"


class PurchaseAlreadyVoidException(ConflictException):
    error_code = "purchase_already_void"
