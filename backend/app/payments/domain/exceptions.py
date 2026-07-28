from app.shared.domain.exceptions import ConflictException, NotFoundException


class PaymentNotFoundException(NotFoundException):
    error_code = "payment_not_found"


class InvalidPaymentStateTransitionException(ConflictException):
    error_code = "invalid_payment_state_transition"
