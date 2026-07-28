import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.purchases.domain.entities import Purchase
from app.purchases.domain.exceptions import PurchaseNotFoundException
from app.purchases.domain.repository import IPurchaseRepository
from app.purchases.infrastructure.mappers import (
    apply_domain_to_existing_model,
    domain_to_model,
    model_to_domain,
)
from app.purchases.infrastructure.models import PurchaseModel
from app.shared.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemyPurchaseRepository(IPurchaseRepository):
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> AsyncSession:
        return self._uow.session

    async def get_by_id_for_business(self, purchase_id: uuid.UUID, business_id: uuid.UUID) -> Purchase | None:
        stmt = select(PurchaseModel).where(
            PurchaseModel.id == purchase_id, PurchaseModel.business_id == business_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model_to_domain(model) if model else None

    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Purchase], int]:
        total = (
            await self._session.execute(
                select(func.count())
                .select_from(PurchaseModel)
                .where(PurchaseModel.business_id == business_id)
            )
        ).scalar_one()
        stmt = (
            select(PurchaseModel)
            .where(PurchaseModel.business_id == business_id)
            .order_by(PurchaseModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        purchases = [model_to_domain(m) for m in result.scalars().all()]
        return purchases, total

    def add(self, purchase: Purchase) -> None:
        self._session.add(domain_to_model(purchase))
        self._uow.collect_events(purchase)

    async def update(self, purchase: Purchase) -> None:
        model = await self._session.get(PurchaseModel, purchase.id)
        if model is None:
            raise PurchaseNotFoundException(f"Purchase {purchase.id} not found")
        apply_domain_to_existing_model(purchase, model)
        self._uow.collect_events(purchase)
