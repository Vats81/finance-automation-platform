import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.sales.application.ports import SalesUnitOfWork
from app.sales.domain.entities import Sale
from app.sales.domain.value_objects import SaleLineItem
from app.shared.domain.value_objects import Money


@dataclass(frozen=True)
class CreateSaleLineItemInput:
    line_number: int
    description: str
    quantity: Decimal
    unit_price: Decimal


@dataclass(frozen=True)
class CreateSaleCommand:
    business_id: uuid.UUID
    invoice_number: str
    invoice_date: date
    line_items: list[CreateSaleLineItemInput]
    customer_id: uuid.UUID | None = None
    due_date: date | None = None
    discount: Decimal | None = None
    tax: Decimal | None = None
    notes: str | None = None


class CreateSaleUseCase:
    def __init__(self, uow: SalesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: CreateSaleCommand) -> Sale:
        line_items = [
            SaleLineItem(
                line_number=item.line_number,
                description=item.description,
                quantity=item.quantity,
                unit_price=Money(amount=item.unit_price),
            )
            for item in command.line_items
        ]
        sale = Sale.create(
            business_id=command.business_id,
            invoice_number=command.invoice_number,
            customer_id=command.customer_id,
            invoice_date=command.invoice_date,
            due_date=command.due_date,
            line_items=line_items,
            discount=Money(amount=command.discount) if command.discount is not None else None,
            tax=Money(amount=command.tax) if command.tax is not None else None,
            notes=command.notes,
        )
        self._uow.sales.add(sale)
        await self._uow.commit()
        return sale
