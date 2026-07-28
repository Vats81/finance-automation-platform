import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.domain.entities import User
from app.identity.domain.exceptions import UserNotFoundException
from app.identity.domain.repository import IUserRepository
from app.identity.infrastructure.mappers import (
    apply_domain_to_existing_model,
    domain_to_model,
    model_to_domain,
)
from app.identity.infrastructure.models import UserModel
from app.shared.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemyUserRepository(IUserRepository):
    """Takes the owning UnitOfWork (not a bare session) so that `add`/`update`
    can register the aggregate's pending domain events with
    `uow.collect_events(...)` — see SqlAlchemyUnitOfWork.commit(), which is
    where those events are flushed to the outbox in the same transaction.
    """

    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> AsyncSession:
        return self._uow.session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return model_to_domain(model) if model else None

    async def get_by_entra_object_id(self, entra_object_id: str) -> User | None:
        stmt = select(UserModel).where(UserModel.entra_object_id == entra_object_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model_to_domain(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model_to_domain(model) if model else None

    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[User], int]:
        total = (await self._session.execute(select(func.count()).select_from(UserModel))).scalar_one()
        stmt = select(UserModel).order_by(UserModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        users = [model_to_domain(m) for m in result.scalars().all()]
        return users, total

    def add(self, user: User) -> None:
        self._session.add(domain_to_model(user))
        self._uow.collect_events(user)

    async def update(self, user: User) -> None:
        model = await self._session.get(UserModel, user.id)
        if model is None:
            raise UserNotFoundException(f"User {user.id} not found")
        apply_domain_to_existing_model(user, model)
        self._uow.collect_events(user)
