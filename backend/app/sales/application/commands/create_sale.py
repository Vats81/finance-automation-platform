import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.sales.application.ports import SalesUnitOfWork
from app.sales.domain.entities import Sale
from app.sales.domain.exceptions import DuplicateInvoiceNumberException
from app.sales.domain.value_objects import SaleLineItem
from app.shared.domain.value_objects import Money


@dataclass(frozen=True)
class CreateSaleLineItemInput:
    line_number: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    gst_rate: Decimal | None = None
    hsn_code: str | None = None


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
    place_of_supply: str | None = None


class CreateSaleUseCase:
    def __init__(self, uow: SalesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: CreateSaleCommand) -> Sale:
        if await self._uow.sales.invoice_number_in_use(command.business_id, command.invoice_number):
            raise DuplicateInvoiceNumberException(
                f"Invoice number {command.invoice_number!r} is already used by another sale in this business."
            )
        line_items = [
            SaleLineItem(
                line_number=item.line_number,
                description=item.description,
                quantity=item.quantity,
                unit_price=Money(amount=item.unit_price),
                gst_rate=item.gst_rate,
                hsn_code=item.hsn_code,
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
            place_of_supply=command.place_of_supply,
        )
        self._uow.sales.add(sale)
        await self._uow.commit()
        return sale
