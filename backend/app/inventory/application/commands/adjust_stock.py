import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.inventory.application.ports import InventoryUnitOfWork
from app.inventory.domain.entities import Product
from app.inventory.domain.exceptions import ProductNotFoundException


@dataclass(frozen=True)
class AdjustStockCommand:
    business_id: uuid.UUID
    product_id: uuid.UUID
    delta: Decimal
    reason: str


class AdjustStockUseCase:
    def __init__(self, uow: InventoryUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: AdjustStockCommand) -> Product:
        product = await self._uow.products.get_by_id_for_business(command.product_id, command.business_id)
        if product is None:
            raise ProductNotFoundException(f"Product {command.product_id} not found")

        product.adjust_stock(delta=command.delta, reason=command.reason)
        await self._uow.products.update(product)
        await self._uow.commit()
        return product
