from dataclasses import dataclass

from app.identity.application.ports import IdentityUnitOfWork
from app.identity.domain.entities import User
from app.shared.application.pagination import Page, PageRequest


@dataclass(frozen=True)
class ListUsersQuery:
    page: PageRequest


class ListUsersUseCase:
    def __init__(self, uow: IdentityUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListUsersQuery) -> Page[User]:
        users, total = await self._uow.users.list_all(offset=query.page.offset, limit=query.page.limit)
        return Page(items=users, total=total, offset=query.page.offset, limit=query.page.limit)
