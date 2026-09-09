import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.purchases.application.ports import PurchasesUnitOfWork
from app.purchases.domain.entities import Purchase
from app.purchases.domain.exceptions import PurchaseNotFoundException
from app.purchases.domain.value_objects import PurchaseLineItem
from app.shared.domain.value_objects import Money


@dataclass(frozen=True)
class UpdatePurchaseLineItemInput:
    line_number: int
    description: str
    quantity: Decimal
    unit_cost: Decimal
    product_id: uuid.UUID | None = None


@dataclass(frozen=True)
class UpdatePurchaseCommand:
    business_id: uuid.UUID
    purchase_id: uuid.UUID
    purchase_number: str
    vendor_id: uuid.UUID
    purchase_date: date
    line_items: list[UpdatePurchaseLineItemInput]
    due_date: date | None = None
    tax: Decimal | None = None
    notes: str | None = None


class UpdatePurchaseUseCase:
    def __init__(self, uow: PurchasesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: UpdatePurchaseCommand) -> Purchase:
        purchase = await self._uow.purchases.get_by_id_for_business(command.purchase_id, command.business_id)
        if purchase is None:
            raise PurchaseNotFoundException(f"Purchase {command.purchase_id} not found")

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
        tax = Money(amount=command.tax) if command.tax is not None else Money(amount=Decimal("0"))
        purchase.update_details(
            purchase_number=command.purchase_number,
            vendor_id=command.vendor_id,
            purchase_date=command.purchase_date,
            due_date=command.due_date,
            line_items=line_items,
            tax=tax,
            notes=command.notes,
        )
        await self._uow.purchases.update(purchase)
        await self._uow.commit()
        return purchase
