import enum


class ExpenseStatus(str, enum.Enum):
    RECORDED = "recorded"
    VOID = "void"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    UPI = "upi"
    OTHER = "other"
