from app.shared.domain.exceptions import NotFoundException


class CustomerNotFoundException(NotFoundException):
    error_code = "customer_not_found"
