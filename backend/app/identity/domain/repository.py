import uuid
from abc import ABC, abstractmethod

from app.identity.domain.entities import User


class IUserRepository(ABC):
    """Repository interface — domain vocabulary, one per aggregate (Evans).
    Implemented by identity/infrastructure/repository_impl.py against
    SQLAlchemy; the domain and application layers never import SQLAlchemy.
    """

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...

    @abstractmethod
    async def get_by_entra_object_id(self, entra_object_id: str) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[User], int]: ...

    @abstractmethod
    def add(self, user: User) -> None: ...

    @abstractmethod
    async def update(self, user: User) -> None: ...
