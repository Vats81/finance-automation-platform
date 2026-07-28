from app.shared.domain.exceptions import ConflictException, NotFoundException, ValidationException


class PurchaseOrderNotFoundException(NotFoundException):
    error_code = "purchase_order_not_found"


class PurchaseOrderNotOpenException(ConflictException):
    """Raised when an action requires an OPEN PO (e.g. matching an invoice
    against it) but it has been closed or cancelled.
    """

    error_code = "purchase_order_not_open"


class EmptyPurchaseOrderException(ValidationException):
    error_code = "empty_purchase_order"
