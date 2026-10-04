from fastapi import Depends

from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.contact.application.ports import IContactRequestStore
from app.contact.infrastructure.store_impl import SqlAlchemyContactRequestStore


async def get_contact_request_store(uow: AppUnitOfWork = Depends(get_uow)) -> IContactRequestStore:
    return SqlAlchemyContactRequestStore(uow.session)
