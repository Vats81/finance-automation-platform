import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.customers.domain.entities import Customer
from app.customers.domain.exceptions import CustomerNotFoundException
from app.customers.domain.repository import ICustomerRepository
from app.customers.infrastructure.mappers import (
    apply_domain_to_existing_model,
    domain_to_model,
    model_to_domain,
)
from app.customers.infrastructure.models import CustomerModel
from app.shared.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemyCustomerRepository(ICustomerRepository):
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> AsyncSession:
        return self._uow.session

    async def get_by_id_for_business(self, customer_id: uuid.UUID, business_id: uuid.UUID) -> Customer | None:
        stmt = select(CustomerModel).where(
            CustomerModel.id == customer_id, CustomerModel.business_id == business_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model_to_domain(model) if model else None

    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Customer], int]:
        total = (
            await self._session.execute(
                select(func.count())
                .select_from(CustomerModel)
                .where(CustomerModel.business_id == business_id)
            )
        ).scalar_one()
        stmt = (
            select(CustomerModel)
            .where(CustomerModel.business_id == business_id)
            .order_by(CustomerModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        customers = [model_to_domain(m) for m in result.scalars().all()]
        return customers, total

    def add(self, customer: Customer) -> None:
        self._session.add(domain_to_model(customer))
        self._uow.collect_events(customer)

    async def update(self, customer: Customer) -> None:
        model = await self._session.get(CustomerModel, customer.id)
        if model is None:
            raise CustomerNotFoundException(f"Customer {customer.id} not found")
        apply_domain_to_existing_model(customer, model)
        self._uow.collect_events(customer)
