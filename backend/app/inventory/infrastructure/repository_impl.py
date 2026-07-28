import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.inventory.domain.entities import Product
from app.inventory.domain.exceptions import ProductNotFoundException
from app.inventory.domain.repository import IProductRepository
from app.inventory.infrastructure.mappers import (
    apply_domain_to_existing_model,
    domain_to_model,
    model_to_domain,
)
from app.inventory.infrastructure.models import ProductModel
from app.shared.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemyProductRepository(IProductRepository):
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> AsyncSession:
        return self._uow.session

    async def get_by_id_for_business(self, product_id: uuid.UUID, business_id: uuid.UUID) -> Product | None:
        stmt = select(ProductModel).where(
            ProductModel.id == product_id, ProductModel.business_id == business_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model_to_domain(model) if model else None

    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Product], int]:
        total = (
            await self._session.execute(
                select(func.count()).select_from(ProductModel).where(ProductModel.business_id == business_id)
            )
        ).scalar_one()
        stmt = (
            select(ProductModel)
            .where(ProductModel.business_id == business_id)
            .order_by(ProductModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        products = [model_to_domain(m) for m in result.scalars().all()]
        return products, total

    def add(self, product: Product) -> None:
        self._session.add(domain_to_model(product))
        self._uow.collect_events(product)

    async def update(self, product: Product) -> None:
        model = await self._session.get(ProductModel, product.id)
        if model is None:
            raise ProductNotFoundException(f"Product {product.id} not found")
        apply_domain_to_existing_model(product, model)
        self._uow.collect_events(product)
