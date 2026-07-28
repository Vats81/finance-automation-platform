import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.inventory.application.ports import InventoryUnitOfWork
from app.inventory.domain.entities import Product
from app.shared.domain.value_objects import Money


@dataclass(frozen=True)
class CreateProductCommand:
    business_id: uuid.UUID
    name: str
    sku: str
    selling_price: Decimal
    purchase_cost: Decimal
    category: str | None = None
    current_quantity: Decimal = Decimal("0")
    minimum_stock_level: Decimal = Decimal("0")
    reorder_quantity: Decimal = Decimal("0")
    unit_of_measurement: str = "unit"
    vendor_id: uuid.UUID | None = None


class CreateProductUseCase:
    def __init__(self, uow: InventoryUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: CreateProductCommand) -> Product:
        product = Product.create(
            business_id=command.business_id,
            name=command.name,
            sku=command.sku,
            selling_price=Money(amount=command.selling_price),
            purchase_cost=Money(amount=command.purchase_cost),
            category=command.category,
            current_quantity=command.current_quantity,
            minimum_stock_level=command.minimum_stock_level,
            reorder_quantity=command.reorder_quantity,
            unit_of_measurement=command.unit_of_measurement,
            vendor_id=command.vendor_id,
        )
        self._uow.products.add(product)
        await self._uow.commit()
        return product
