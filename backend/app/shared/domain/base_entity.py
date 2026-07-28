import uuid
from abc import ABC


class Entity(ABC):
    """Base class for domain entities: identity-based equality, framework-agnostic."""

    def __init__(self, entity_id: uuid.UUID | None = None) -> None:
        self.id: uuid.UUID = entity_id or uuid.uuid4()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        if type(self) is not type(other):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash((type(self), self.id))

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id})"
