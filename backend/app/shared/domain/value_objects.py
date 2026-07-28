from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.shared.domain.base_value_object import ValueObject
from app.shared.domain.exceptions import ValidationException

_CENTS = Decimal("0.01")


@dataclass(frozen=True)
class Money(ValueObject):
    """Explicit Shared Kernel: unlike EmailAddress/TaxId/Address (deliberately
    duplicated per bounded context, see vendors/domain/value_objects.py),
    Money is genuinely shared between purchase_orders, invoices, and
    payments — 2-way/3-way matching (invoices/domain/matching/) requires PO
    and Invoice line-item totals to be numerically comparable, which is only
    safe if every context uses the identical representation and rounding
    rules for currency.
    """

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.currency != "USD":
            raise ValidationException("Only USD is supported in the foundation slice")
        quantized = self.amount.quantize(_CENTS, rounding=ROUND_HALF_UP)
        object.__setattr__(self, "amount", quantized)

    @classmethod
    def from_cents(cls, cents: int, currency: str = "USD") -> "Money":
        return cls(amount=Decimal(cents) / 100, currency=currency)

    @property
    def cents(self) -> int:
        return int(self.amount * 100)

    def _check_same_currency(self, other: "Money") -> None:
        if other.currency != self.currency:
            raise ValidationException(f"Cannot combine {self.currency} with {other.currency}")

    def __add__(self, other: "Money") -> "Money":
        self._check_same_currency(other)
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check_same_currency(other)
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def __mul__(self, multiplier: Decimal | int) -> "Money":
        return Money(amount=self.amount * Decimal(multiplier), currency=self.currency)

    def __lt__(self, other: "Money") -> bool:
        self._check_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        self._check_same_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: "Money") -> bool:
        self._check_same_currency(other)
        return self.amount > other.amount

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"
