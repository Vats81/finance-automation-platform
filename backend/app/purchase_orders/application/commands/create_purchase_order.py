import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.purchase_orders.application.ports import PurchaseOrdersUnitOfWork
from app.purchase_orders.domain.entities import PurchaseOrder
from app.purchase_orders.domain.value_objects import PurchaseOrderLineItem
from app.shared.domain.value_objects import Money


@dataclass(frozen=True)
class LineItemInput:
    line_number: int
    description: str
    quantity: Decimal
    unit_price: Decimal


@dataclass(frozen=True)
class CreatePurchaseOrderCommand:
    vendor_id: uuid.UUID
    line_items: list[LineItemInput]


class CreatePurchaseOrderUseCase:
    def __init__(self, uow: PurchaseOrdersUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: CreatePurchaseOrderCommand) -> PurchaseOrder:
        line_items = [
            PurchaseOrderLineItem(
                line_number=item.line_number,
                description=item.description,
                quantity=item.quantity,
                unit_price=Money(amount=item.unit_price),
            )
            for item in command.line_items
        ]
        po = PurchaseOrder.create(vendor_id=command.vendor_id, line_items=line_items)
        self._uow.purchase_orders.add(po)
        await self._uow.commit()
        return po
