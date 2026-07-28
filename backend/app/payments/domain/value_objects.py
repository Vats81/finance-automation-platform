import enum


class PaymentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
