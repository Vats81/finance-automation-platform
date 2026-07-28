from typing import Protocol

from app.identity.domain.repository import IUserRepository


class IdentityUnitOfWork(Protocol):
    """Narrow structural interface (Interface Segregation Principle):
    identity's use cases depend on exactly the repository properties and
    transaction methods they need, not the full AppUnitOfWork (which would
    pull the application layer into knowing about every other context) nor
    the generic SqlAlchemyUnitOfWork (which doesn't declare `users` at all
    — that property only exists on the AppUnitOfWork subclass built in
    bootstrap/unit_of_work.py). Satisfied structurally by AppUnitOfWork at
    runtime; no inheritance relationship required.

    Repos are declared as read-only `@property` getters rather than plain
    attributes: Protocol attribute matching is invariant for mutable
    attributes, which would reject AppUnitOfWork's concrete
    `SqlAlchemyUserRepository` as satisfying `users: IUserRepository`.
    Properties are covariant, so the concrete subtype satisfies the
    interface type as expected.
    """

    @property
    def users(self) -> IUserRepository: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
