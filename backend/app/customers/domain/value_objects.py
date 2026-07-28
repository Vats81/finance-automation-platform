import enum
import re
from dataclasses import dataclass

from app.shared.domain.base_value_object import ValueObject
from app.shared.domain.exceptions import ValidationException

# Deliberately duplicated rather than imported from vendors/identity — see
# vendors/domain/value_objects.py for why bounded contexts define their own
# primitives instead of sharing a ubiquitous language across contexts.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CustomerStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass(frozen=True)
class CustomerEmailAddress(ValueObject):
    value: str

    def __post_init__(self) -> None:
        if not _EMAIL_RE.match(self.value):
            raise ValidationException(f"'{self.value}' is not a valid email address")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CustomerAddress(ValueObject):
    street: str
    city: str
    state: str
    postal_code: str
    country: str = "US"

    def __post_init__(self) -> None:
        if not all([self.street, self.city, self.state, self.postal_code]):
            raise ValidationException("Address requires street, city, state, and postal_code")
