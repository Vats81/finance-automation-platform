import uuid
from dataclasses import dataclass

from app.purchases.application.ports import PurchasesUnitOfWork
from app.purchases.domain.entities import Purchase
from app.purchases.domain.value_objects import PurchasePaymentStatus, PurchaseStatus

# Same rationale as sales/application/queries/list_outstanding_sales.py:
# payment_status is derived, not a stored column, so filtering happens in
# Python after loading every non-void purchase for the business.
_MAX_PURCHASES_TO_SCAN = 10_000


@dataclass(frozen=True)
class ListOutstandingPurchasesQuery:
    business_id: uuid.UUID


class ListOutstandingPurchasesUseCase:
    def __init__(self, uow: PurchasesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListOutstandingPurchasesQuery) -> list[Purchase]:
        purchases, _ = await self._uow.purchases.list_for_business(
            query.business_id, offset=0, limit=_MAX_PURCHASES_TO_SCAN
        )
        outstanding = [
            purchase
            for purchase in purchases
            if purchase.status != PurchaseStatus.VOID
            and purchase.payment_status != PurchasePaymentStatus.PAID
        ]
        outstanding.sort(key=lambda purchase: (purchase.due_date is None, purchase.due_date))
        return outstanding
