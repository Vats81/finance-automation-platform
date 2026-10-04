import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.contact.application.ports import ContactRequest, IContactRequestStore
from app.contact.infrastructure.models import ContactRequestModel


def _to_dto(model: ContactRequestModel) -> ContactRequest:
    return ContactRequest(
        id=model.id,
        name=model.name,
        email=model.email,
        business_name=model.business_name,
        message=model.message,
        notified=model.notified,
        created_at=model.created_at,
    )


class SqlAlchemyContactRequestStore(IContactRequestStore):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self, *, name: str, email: str, business_name: str | None, message: str | None
    ) -> ContactRequest:
        model = ContactRequestModel(
            id=uuid.uuid4(),
            name=name,
            email=email,
            business_name=business_name,
            message=message,
            notified=False,
        )
        self._session.add(model)
        await self._session.commit()
        # created_at is a server default; expire/refresh so the DTO carries
        # the value Postgres actually wrote.
        await self._session.refresh(model)
        return _to_dto(model)

    async def mark_notified(self, request_id: uuid.UUID) -> None:
        await self._session.execute(
            update(ContactRequestModel).where(ContactRequestModel.id == request_id).values(notified=True)
        )
        await self._session.commit()

    async def list_recent(self, *, limit: int) -> list[ContactRequest]:
        result = await self._session.execute(
            select(ContactRequestModel).order_by(ContactRequestModel.created_at.desc()).limit(limit)
        )
        return [_to_dto(m) for m in result.scalars().all()]
