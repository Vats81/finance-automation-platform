import enum
import re
from dataclasses import dataclass

from app.shared.domain.base_value_object import ValueObject
from app.shared.domain.exceptions import ValidationException
from app.shared.domain.gst import clean_gstin

# Bounded contexts intentionally define their own primitives (EmailAddress,
# TaxId, Address) rather than importing from identity/other contexts, even
# though the shapes overlap — sharing value objects across contexts couples
# their ubiquitous languages together, which is exactly what DDD bounded
# contexts exist to avoid. A true Shared Kernel would be a deliberate,
# explicit decision, not a convenience import.

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_EIN_RE = re.compile(r"^\d{2}-?\d{7}$")
_PAN_RE = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$")  # India's Permanent Account Number
_GSTIN_LENGTH = 15


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

    @classmethod
    def not_provided(cls) -> "VendorEmailAddress":
        """A supplier known only by name (added automatically from a purchase). Never accepted from input."""
        blank = object.__new__(cls)
        object.__setattr__(blank, "value", "")
        return blank

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TaxId(ValueObject):
    """A supplier's tax number: an Indian GSTIN or PAN, or a US EIN (##-#######). An EIN or PAN is masked in
    string representation since it is sensitive and should never land unmasked in logs or generic UI; a GSTIN
    is printed on every invoice the supplier issues, so it is shown as it is.
    """

    value: str

    def __post_init__(self) -> None:
        if _EIN_RE.match(self.value) or _PAN_RE.match(self.value):
            return
        # clean_gstin also checks the GSTIN's last character, so a mistyped one is refused
        if len(self.value) == _GSTIN_LENGTH and clean_gstin(self.value) == self.value:
            return
        raise ValidationException(
            f"'{self.value}' is not a valid tax ID. Enter a GSTIN, a PAN, or a US EIN (##-#######)."
        )

    @classmethod
    def not_provided(cls) -> "TaxId":
        blank = object.__new__(cls)
        object.__setattr__(blank, "value", "")
        return blank

    @property
    def unmasked(self) -> str:
        return self.value

    def masked(self) -> str:
        if not self.value:
            return ""
        if _EIN_RE.match(self.value):
            digits = self.value.replace("-", "")
            return f"**-***{digits[-4:]}"
        if _PAN_RE.match(self.value):
            return f"******{self.value[-4:]}"
        return self.value

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

    @classmethod
    def not_provided(cls) -> "Address":
        blank = object.__new__(cls)
        for name in ("street", "city", "state", "postal_code"):
            object.__setattr__(blank, name, "")
        object.__setattr__(blank, "country", "US")
        return blank
