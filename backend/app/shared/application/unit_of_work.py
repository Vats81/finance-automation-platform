from abc import ABC, abstractmethod
from types import TracebackType


class IUnitOfWork(ABC):
    """Transaction boundary interface.

    A concrete UoW (SqlAlchemyUnitOfWork) wraps one AsyncSession, exposes
    typed repository properties per bounded context, and — critically —
    `commit()` is where domain events collected on tracked aggregates are
    written to the outbox table in the SAME transaction as the state change.
    Application-layer use cases depend on this interface only; they never
    import SQLAlchemy.
    """

    async def __aenter__(self) -> "IUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        # Callers must explicitly call commit(); we never auto-commit on clean exit.

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...
