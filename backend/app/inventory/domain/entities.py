import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.inventory.domain.events import (
    ProductCreated,
    ProductDeactivated,
    ProductDetailsUpdated,
    StockAdjusted,
)
from app.inventory.domain.exceptions import NegativeStockException
from app.inventory.domain.value_objects import ProductStatus
from app.shared.domain.aggregate_root import AggregateRoot
from app.shared.domain.value_objects import Money


class Product(AggregateRoot):
    """A product/item in a business's inventory. References Vendor only by
    id (never loads/mutates it — same reasoning as every other
    cross-aggregate reference in this codebase). No cross-context wiring to
    Sales/Purchases in this slice — stock changes are manual via
    adjust_stock(); auto-decrementing on a sale is a future slice's concern.
    """

    def __init__(
        self,
        *,
        entity_id: uuid.UUID | None = None,
        business_id: uuid.UUID,
        name: str,
        sku: str,
        category: str | None = None,
        selling_price: Money,
        purchase_cost: Money,
        current_quantity: Decimal = Decimal("0"),
        minimum_stock_level: Decimal = Decimal("0"),
        reorder_quantity: Decimal = Decimal("0"),
        unit_of_measurement: str = "unit",
        vendor_id: uuid.UUID | None = None,
        status: ProductStatus = ProductStatus.ACTIVE,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.business_id = business_id
        self.name = name
        self.sku = sku
        self.category = category
        self.selling_price = selling_price
        self.purchase_cost = purchase_cost
        self.current_quantity = current_quantity
        self.minimum_stock_level = minimum_stock_level
        self.reorder_quantity = reorder_quantity
        self.unit_of_measurement = unit_of_measurement
        self.vendor_id = vendor_id
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)

    @classmethod
    def create(
        cls,
        *,
        business_id: uuid.UUID,
        name: str,
        sku: str,
        selling_price: Money,
        purchase_cost: Money,
        category: str | None = None,
        current_quantity: Decimal = Decimal("0"),
        minimum_stock_level: Decimal = Decimal("0"),
        reorder_quantity: Decimal = Decimal("0"),
        unit_of_measurement: str = "unit",
        vendor_id: uuid.UUID | None = None,
    ) -> "Product":
        product = cls(
            business_id=business_id,
            name=name,
            sku=sku,
            category=category,
            selling_price=selling_price,
            purchase_cost=purchase_cost,
            current_quantity=current_quantity,
            minimum_stock_level=minimum_stock_level,
            reorder_quantity=reorder_quantity,
            unit_of_measurement=unit_of_measurement,
            vendor_id=vendor_id,
        )
        product._record_event(
            ProductCreated(aggregate_id=product.id, business_id=str(business_id), name=name, sku=sku)
        )
        return product

    @property
    def is_out_of_stock(self) -> bool:
        return self.current_quantity <= 0

    @property
    def is_low_stock(self) -> bool:
        return 0 < self.current_quantity <= self.minimum_stock_level

    @property
    def stock_value(self) -> Money:
        return self.purchase_cost * self.current_quantity

    def update_details(
        self,
        *,
        name: str | None = None,
        category: str | None = None,
        selling_price: Money | None = None,
        purchase_cost: Money | None = None,
        minimum_stock_level: Decimal | None = None,
        reorder_quantity: Decimal | None = None,
    ) -> None:
        changed: list[str] = []
        if name is not None and name != self.name:
            self.name = name
            changed.append("name")
        if category is not None and category != self.category:
            self.category = category
            changed.append("category")
        if selling_price is not None and selling_price != self.selling_price:
            self.selling_price = selling_price
            changed.append("selling_price")
        if purchase_cost is not None and purchase_cost != self.purchase_cost:
            self.purchase_cost = purchase_cost
            changed.append("purchase_cost")
        if minimum_stock_level is not None and minimum_stock_level != self.minimum_stock_level:
            self.minimum_stock_level = minimum_stock_level
            changed.append("minimum_stock_level")
        if reorder_quantity is not None and reorder_quantity != self.reorder_quantity:
            self.reorder_quantity = reorder_quantity
            changed.append("reorder_quantity")

        if changed:
            self._record_event(ProductDetailsUpdated(aggregate_id=self.id, changed_fields=changed))

    def adjust_stock(self, *, delta: Decimal, reason: str) -> None:
        new_quantity = self.current_quantity + delta
        if new_quantity < 0:
            raise NegativeStockException(
                f"Adjusting product {self.id} by {delta} would result in negative stock"
            )

        self.current_quantity = new_quantity
        self._record_event(
            StockAdjusted(aggregate_id=self.id, delta=delta, new_quantity=new_quantity, reason=reason)
        )

    def deactivate(self) -> None:
        self.status = ProductStatus.INACTIVE
        self._record_event(ProductDeactivated(aggregate_id=self.id, name=self.name))

    def reactivate(self) -> None:
        self.status = ProductStatus.ACTIVE

    @property
    def is_active(self) -> bool:
        return self.status == ProductStatus.ACTIVE
