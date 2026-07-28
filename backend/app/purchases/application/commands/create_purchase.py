import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.purchases.application.ports import PurchasesUnitOfWork
from app.purchases.domain.entities import Purchase
from app.purchases.domain.value_objects import PurchaseLineItem
from app.shared.domain.value_objects import Money


@dataclass(frozen=True)
class CreatePurchaseLineItemInput:
    line_number: int
    description: str
    quantity: Decimal
    unit_cost: Decimal
    product_id: uuid.UUID | None = None


@dataclass(frozen=True)
class CreatePurchaseCommand:
    business_id: uuid.UUID
    purchase_number: str
    vendor_id: uuid.UUID
    purchase_date: date
    line_items: list[CreatePurchaseLineItemInput]
    due_date: date | None = None
    tax: Decimal | None = None
    notes: str | None = None


class CreatePurchaseUseCase:
    def __init__(self, uow: PurchasesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: CreatePurchaseCommand) -> Purchase:
        line_items = [
            PurchaseLineItem(
                line_number=item.line_number,
                description=item.description,
                quantity=item.quantity,
                unit_cost=Money(amount=item.unit_cost),
                product_id=item.product_id,
            )
            for item in command.line_items
        ]
        purchase = Purchase.create(
            business_id=command.business_id,
            purchase_number=command.purchase_number,
            vendor_id=command.vendor_id,
            purchase_date=command.purchase_date,
            due_date=command.due_date,
            line_items=line_items,
            tax=Money(amount=command.tax) if command.tax is not None else None,
            notes=command.notes,
        )
        self._uow.purchases.add(purchase)
        await self._uow.commit()
        return purchase
