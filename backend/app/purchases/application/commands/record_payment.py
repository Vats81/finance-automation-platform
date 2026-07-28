import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.purchases.application.ports import PurchasesUnitOfWork
from app.purchases.domain.entities import Purchase
from app.purchases.domain.exceptions import PurchaseNotFoundException
from app.shared.domain.value_objects import Money


@dataclass(frozen=True)
class RecordPurchasePaymentCommand:
    business_id: uuid.UUID
    purchase_id: uuid.UUID
    amount: Decimal


class RecordPurchasePaymentUseCase:
    def __init__(self, uow: PurchasesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: RecordPurchasePaymentCommand) -> Purchase:
        purchase = await self._uow.purchases.get_by_id_for_business(command.purchase_id, command.business_id)
        if purchase is None:
            raise PurchaseNotFoundException(f"Purchase {command.purchase_id} not found")

        purchase.record_payment(Money(amount=command.amount))
        await self._uow.purchases.update(purchase)
        await self._uow.commit()
        return purchase
