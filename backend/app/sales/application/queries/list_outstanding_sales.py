import uuid
from dataclasses import dataclass

from app.sales.application.ports import SalesUnitOfWork
from app.sales.domain.entities import Sale
from app.sales.domain.value_objects import SalePaymentStatus, SaleStatus

# payment_status is derived (not a stored column — see Sale.payment_status),
# so "outstanding" filtering can't happen in SQL; this loads every non-void
# sale for the business and filters in Python. Same accepted tradeoff as
# approvals/infrastructure/repository_impl.py:list_pending_for_role — fine
# at foundation-slice scale, worth a materialized column if this becomes a
# hot path (see PHASE2_ROADMAP.md).
_MAX_SALES_TO_SCAN = 10_000


@dataclass(frozen=True)
class ListOutstandingSalesQuery:
    business_id: uuid.UUID


class ListOutstandingSalesUseCase:
    def __init__(self, uow: SalesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListOutstandingSalesQuery) -> list[Sale]:
        sales, _ = await self._uow.sales.list_for_business(
            query.business_id, offset=0, limit=_MAX_SALES_TO_SCAN
        )
        outstanding = [
            sale
            for sale in sales
            if sale.status != SaleStatus.VOID and sale.payment_status != SalePaymentStatus.PAID
        ]
        outstanding.sort(key=lambda sale: (sale.due_date is None, sale.due_date))
        return outstanding
