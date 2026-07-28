import uuid
from dataclasses import dataclass
from datetime import datetime

from app.bootstrap.unit_of_work import AppUnitOfWork


@dataclass(frozen=True)
class ListUsersOverviewQuery:
    offset: int = 0
    limit: int = 50


@dataclass(frozen=True)
class UserOverviewItem:
    id: uuid.UUID
    email: str
    display_name: str
    is_email_verified: bool
    is_active: bool
    created_at: datetime


@dataclass(frozen=True)
class UsersOverviewPage:
    items: list[UserOverviewItem]
    total: int
    offset: int
    limit: int


class ListUsersOverviewUseCase:
    """Thin wrapper over the already-existing, already-platform-wide
    IUserRepository.list_all — no new repository method needed here.
    """

    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListUsersOverviewQuery) -> UsersOverviewPage:
        users, total = await self._uow.users.list_all(offset=query.offset, limit=query.limit)
        items = [
            UserOverviewItem(
                id=user.id,
                email=str(user.email),
                display_name=user.display_name,
                is_email_verified=user.is_email_verified,
                is_active=user.is_active,
                created_at=user.created_at,
            )
            for user in users
        ]
        return UsersOverviewPage(items=items, total=total, offset=query.offset, limit=query.limit)
