import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.sales.domain.entities import Sale
from app.sales.domain.exceptions import SaleNotFoundException
from app.sales.domain.repository import ISaleRepository
from app.sales.infrastructure.mappers import (
    apply_domain_to_existing_model,
    domain_to_model,
    model_to_domain,
)
from app.sales.infrastructure.models import SaleModel
from app.shared.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemySaleRepository(ISaleRepository):
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> AsyncSession:
        return self._uow.session

    async def get_by_id_for_business(self, sale_id: uuid.UUID, business_id: uuid.UUID) -> Sale | None:
        stmt = select(SaleModel).where(SaleModel.id == sale_id, SaleModel.business_id == business_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model_to_domain(model) if model else None

    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Sale], int]:
        total = (
            await self._session.execute(
                select(func.count()).select_from(SaleModel).where(SaleModel.business_id == business_id)
            )
        ).scalar_one()
        stmt = (
            select(SaleModel)
            .where(SaleModel.business_id == business_id)
            .order_by(SaleModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        sales = [model_to_domain(m) for m in result.scalars().all()]
        return sales, total

    def add(self, sale: Sale) -> None:
        self._session.add(domain_to_model(sale))
        self._uow.collect_events(sale)

    async def update(self, sale: Sale) -> None:
        model = await self._session.get(SaleModel, sale.id)
        if model is None:
            raise SaleNotFoundException(f"Sale {sale.id} not found")
        apply_domain_to_existing_model(sale, model)
        self._uow.collect_events(sale)
