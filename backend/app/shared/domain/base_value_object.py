from abc import ABC
from dataclasses import fields, is_dataclass


class ValueObject(ABC):
    """Base for immutable value objects: structural equality, no identity.

    Concrete value objects should be declared as `@dataclass(frozen=True)` subclasses.
    """

    def __eq__(self, other: object) -> bool:
        if not is_dataclass(self) or type(self) is not type(other):
            return NotImplemented
        return all(
            getattr(self, f.name) == getattr(other, f.name) for f in fields(self)
        )

    def __hash__(self) -> int:
        if not is_dataclass(self):
            return object.__hash__(self)
        return hash(tuple(getattr(self, f.name) for f in fields(self)))
