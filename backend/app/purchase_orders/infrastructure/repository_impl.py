import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.purchase_orders.domain.entities import PurchaseOrder
from app.purchase_orders.domain.exceptions import PurchaseOrderNotFoundException
from app.purchase_orders.domain.repository import IPurchaseOrderRepository
from app.purchase_orders.infrastructure.mappers import (
    apply_domain_to_existing_model,
    domain_to_model,
    model_to_domain,
)
from app.purchase_orders.infrastructure.models import PurchaseOrderModel
from app.shared.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemyPurchaseOrderRepository(IPurchaseOrderRepository):
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> AsyncSession:
        return self._uow.session

    async def get_by_id(self, po_id: uuid.UUID) -> PurchaseOrder | None:
        model = await self._session.get(PurchaseOrderModel, po_id)
        return model_to_domain(model) if model else None

    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[PurchaseOrder], int]:
        count_result = await self._session.execute(select(func.count()).select_from(PurchaseOrderModel))
        total = count_result.scalar_one()
        stmt = (
            select(PurchaseOrderModel)
            .order_by(PurchaseOrderModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        pos = [model_to_domain(m) for m in result.scalars().all()]
        return pos, total

    def add(self, purchase_order: PurchaseOrder) -> None:
        self._session.add(domain_to_model(purchase_order))
        self._uow.collect_events(purchase_order)

    async def update(self, purchase_order: PurchaseOrder) -> None:
        model = await self._session.get(PurchaseOrderModel, purchase_order.id)
        if model is None:
            raise PurchaseOrderNotFoundException(f"PurchaseOrder {purchase_order.id} not found")
        apply_domain_to_existing_model(purchase_order, model)
        self._uow.collect_events(purchase_order)
