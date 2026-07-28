import uuid
from dataclasses import dataclass

from app.inventory.application.ports import InventoryUnitOfWork
from app.inventory.domain.entities import Product
from app.inventory.domain.exceptions import ProductNotFoundException


@dataclass(frozen=True)
class GetProductQuery:
    business_id: uuid.UUID
    product_id: uuid.UUID


class GetProductUseCase:
    def __init__(self, uow: InventoryUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: GetProductQuery) -> Product:
        product = await self._uow.products.get_by_id_for_business(query.product_id, query.business_id)
        if product is None:
            raise ProductNotFoundException(f"Product {query.product_id} not found")
        return product
