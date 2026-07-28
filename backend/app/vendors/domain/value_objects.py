import enum
import re
from dataclasses import dataclass

from app.shared.domain.base_value_object import ValueObject
from app.shared.domain.exceptions import ValidationException

# Bounded contexts intentionally define their own primitives (EmailAddress,
# TaxId, Address) rather than importing from identity/other contexts, even
# though the shapes overlap — sharing value objects across contexts couples
# their ubiquitous languages together, which is exactly what DDD bounded
# contexts exist to avoid. A true Shared Kernel would be a deliberate,
# explicit decision, not a convenience import.

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_EIN_RE = re.compile(r"^\d{2}-?\d{7}$")


class VendorStatus(str, enum.Enum):
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass(frozen=True)
class VendorEmailAddress(ValueObject):
    value: str

    def __post_init__(self) -> None:
        if not _EMAIL_RE.match(self.value):
            raise ValidationException(f"'{self.value}' is not a valid email address")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TaxId(ValueObject):
    """US EIN (##-#######). Masked in string representation since this is
    sensitive PII that should never land unmasked in logs or generic UI.
    """

    value: str

    def __post_init__(self) -> None:
        if not _EIN_RE.match(self.value):
            raise ValidationException(f"'{self.value}' is not a valid EIN (expected ##-#######)")

    @property
    def unmasked(self) -> str:
        return self.value

    def masked(self) -> str:
        digits = self.value.replace("-", "")
        return f"**-***{digits[-4:]}"

    def __str__(self) -> str:
        return self.masked()


@dataclass(frozen=True)
class Address(ValueObject):
    street: str
    city: str
    state: str
    postal_code: str
    country: str = "US"

    def __post_init__(self) -> None:
        if not all([self.street, self.city, self.state, self.postal_code]):
            raise ValidationException("Address requires street, city, state, and postal_code")
