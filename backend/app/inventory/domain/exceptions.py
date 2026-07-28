from app.shared.domain.exceptions import NotFoundException, ValidationException


class ProductNotFoundException(NotFoundException):
    error_code = "product_not_found"


class NegativeStockException(ValidationException):
    error_code = "negative_stock"
