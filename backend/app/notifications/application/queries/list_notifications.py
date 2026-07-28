import uuid
from dataclasses import dataclass
from typing import Literal

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.inventory.application.queries.list_products import ListProductsQuery, ListProductsUseCase
from app.purchases.application.queries.list_outstanding_purchases import (
    ListOutstandingPurchasesQuery,
    ListOutstandingPurchasesUseCase,
)
from app.sales.application.queries.list_outstanding_sales import (
    ListOutstandingSalesQuery,
    ListOutstandingSalesUseCase,
)
from app.shared.application.pagination import PageRequest
from app.shared.application.ports import IClock

_OVERDUE_CRITICAL_THRESHOLD_DAYS = 7

Category = Literal["overdue_sale", "overdue_purchase", "low_stock"]
Severity = Literal["warning", "critical"]


@dataclass(frozen=True)
class GetNotificationsQuery:
    business_id: uuid.UUID


@dataclass(frozen=True)
class Notification:
    id: str
    category: Category
    severity: Severity
    message: str
    link: str


@dataclass(frozen=True)
class Notifications:
    count: int
    items: list[Notification]


class ListNotificationsUseCase:
    """A real-time snapshot of actionable conditions, not a persisted
    read/unread log — re-queries the same overdue-sales/overdue-purchases/
    low-stock use cases already used elsewhere (Payments dashboard, Business
    Health Score) rather than depending on the outbox/Celery event pipeline,
    which never actually runs a consumer in this dev environment.

    Uses `clock.now()` rather than `date.today()` so this stays
    deterministically unit-testable via the existing FakeClock fake.
    """

    def __init__(self, uow: AppUnitOfWork, clock: IClock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, query: GetNotificationsQuery) -> Notifications:
        today = self._clock.now().date()

        sales = await ListOutstandingSalesUseCase(self._uow).execute(
            ListOutstandingSalesQuery(business_id=query.business_id)
        )
        purchases = await ListOutstandingPurchasesUseCase(self._uow).execute(
            ListOutstandingPurchasesQuery(business_id=query.business_id)
        )
        # PageRequest caps limit at 200 (shared/application/pagination.py) —
        # same accepted scale limit already applied in
        # ai_assistant/application/tools.py and get_business_health_score.py.
        products = await ListProductsUseCase(self._uow).execute(
            ListProductsQuery(business_id=query.business_id, page=PageRequest(offset=0, limit=200))
        )

        sale_notifications = [
            Notification(
                id=f"overdue_sale:{sale.id}",
                category="overdue_sale",
                severity="critical"
                if (today - sale.due_date).days > _OVERDUE_CRITICAL_THRESHOLD_DAYS
                else "warning",
                message=(
                    f"Invoice {sale.invoice_number} is overdue by {(today - sale.due_date).days} "
                    f"day(s) (${sale.outstanding_amount.amount})"
                ),
                link=f"/app/sales/{sale.id}",
            )
            for sale in sales
            if sale.due_date is not None and sale.due_date < today
        ]

        purchase_notifications = [
            Notification(
                id=f"overdue_purchase:{purchase.id}",
                category="overdue_purchase",
                severity="critical"
                if (today - purchase.due_date).days > _OVERDUE_CRITICAL_THRESHOLD_DAYS
                else "warning",
                message=(
                    f"Purchase {purchase.purchase_number} payment is overdue by "
                    f"{(today - purchase.due_date).days} day(s) (${purchase.outstanding_amount.amount})"
                ),
                link=f"/app/purchases/{purchase.id}",
            )
            for purchase in purchases
            if purchase.due_date is not None and purchase.due_date < today
        ]

        stock_notifications = []
        for product in products.items:
            if product.is_out_of_stock:
                stock_notifications.append(
                    Notification(
                        id=f"low_stock:{product.id}",
                        category="low_stock",
                        severity="critical",
                        message=f"{product.name} is out of stock",
                        link=f"/app/inventory/{product.id}",
                    )
                )
            elif product.is_low_stock:
                stock_notifications.append(
                    Notification(
                        id=f"low_stock:{product.id}",
                        category="low_stock",
                        severity="warning",
                        message=f"{product.name} is low on stock ({product.current_quantity} left)",
                        link=f"/app/inventory/{product.id}",
                    )
                )

        items = sale_notifications + purchase_notifications + stock_notifications
        items.sort(key=lambda n: n.severity != "critical")

        return Notifications(count=len(items), items=items)
