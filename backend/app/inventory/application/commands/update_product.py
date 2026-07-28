import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.inventory.application.ports import InventoryUnitOfWork
from app.inventory.domain.entities import Product
from app.inventory.domain.exceptions import ProductNotFoundException
from app.shared.domain.value_objects import Money


@dataclass(frozen=True)
class UpdateProductCommand:
    business_id: uuid.UUID
    product_id: uuid.UUID
    name: str | None = None
    category: str | None = None
    selling_price: Decimal | None = None
    purchase_cost: Decimal | None = None
    minimum_stock_level: Decimal | None = None
    reorder_quantity: Decimal | None = None


class UpdateProductUseCase:
    def __init__(self, uow: InventoryUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: UpdateProductCommand) -> Product:
        product = await self._uow.products.get_by_id_for_business(command.product_id, command.business_id)
        if product is None:
            raise ProductNotFoundException(f"Product {command.product_id} not found")

        product.update_details(
            name=command.name,
            category=command.category,
            selling_price=Money(amount=command.selling_price) if command.selling_price is not None else None,
            purchase_cost=Money(amount=command.purchase_cost) if command.purchase_cost is not None else None,
            minimum_stock_level=command.minimum_stock_level,
            reorder_quantity=command.reorder_quantity,
        )
        await self._uow.products.update(product)
        await self._uow.commit()
        return product
