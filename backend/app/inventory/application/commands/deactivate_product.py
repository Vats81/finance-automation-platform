import uuid
from dataclasses import dataclass

from app.inventory.application.ports import InventoryUnitOfWork
from app.inventory.domain.entities import Product
from app.inventory.domain.exceptions import ProductNotFoundException


@dataclass(frozen=True)
class DeactivateProductCommand:
    business_id: uuid.UUID
    product_id: uuid.UUID


class DeactivateProductUseCase:
    def __init__(self, uow: InventoryUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: DeactivateProductCommand) -> Product:
        product = await self._uow.products.get_by_id_for_business(command.product_id, command.business_id)
        if product is None:
            raise ProductNotFoundException(f"Product {command.product_id} not found")

        product.deactivate()
        await self._uow.products.update(product)
        await self._uow.commit()
        return product
