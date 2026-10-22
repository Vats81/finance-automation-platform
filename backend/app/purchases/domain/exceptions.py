from app.shared.domain.exceptions import ConflictException, NotFoundException, ValidationException


class PurchaseNotFoundException(NotFoundException):
    error_code = "purchase_not_found"


class EmptyPurchaseException(ValidationException):
    error_code = "empty_purchase"


class PurchasePaymentExceedsOutstandingException(ValidationException):
    error_code = "purchase_payment_exceeds_outstanding"


class StockAlreadyUsedException(ConflictException):
    """Voiding a purchase that added stock would take more units out than are
    left (some were already used or sold). Nothing is changed.
    """

    error_code = "stock_already_used"


class PurchaseStockLockedException(ValidationException):
    error_code = "purchase_stock_locked"


class PurchaseAlreadyVoidException(ConflictException):
    error_code = "purchase_already_void"
