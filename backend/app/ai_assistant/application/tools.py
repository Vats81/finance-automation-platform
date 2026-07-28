import uuid
from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.customers.application.queries.list_customers import ListCustomersQuery, ListCustomersUseCase
from app.dashboard.application.queries.get_dashboard_summary import (
    GetDashboardSummaryQuery,
    GetDashboardSummaryUseCase,
)
from app.expenses.application.queries.list_expenses import ListExpensesQuery, ListExpensesUseCase
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

# Read-only tools exposed to the AI assistant — every one is a thin wrapper
# around an existing, already-tested query use case (Phases 2-3). No new
# use cases are written here; a 7th "insights"/health-score tool is
# deferred to a later Phase 4 slice.

ToolHandler = Callable[..., Awaitable[dict[str, Any]]]

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "get_business_summary",
        "description": (
            "Get total revenue, total expenses, net profit, and outstanding receivables for a date range."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "ISO date, e.g. 2026-07-01"},
                "end_date": {"type": "string", "description": "ISO date, e.g. 2026-07-31"},
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "list_outstanding_sales",
        "description": (
            "List unpaid or partially-paid sales (accounts receivable — who owes the business money)."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_outstanding_purchases",
        "description": (
            "List unpaid or partially-paid purchases (accounts payable — who the business owes money to)."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_low_stock_products",
        "description": "List products that are low on stock or out of stock.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_recent_expenses",
        "description": "List the most recently recorded expenses.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max number of expenses, default 10"}
            },
        },
    },
    {
        "name": "list_customers",
        "description": "List the business's customers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max number of customers, default 20"}
            },
        },
    },
]


async def _handle_get_business_summary(
    uow: AppUnitOfWork, business_id: uuid.UUID, *, start_date: str, end_date: str
) -> dict[str, Any]:
    summary = await GetDashboardSummaryUseCase(uow).execute(
        GetDashboardSummaryQuery(
            business_id=business_id,
            start_date=date.fromisoformat(start_date),
            end_date=date.fromisoformat(end_date),
        )
    )
    return {
        "total_revenue": str(summary.total_revenue),
        "total_expenses": str(summary.total_expenses),
        "net_profit": str(summary.net_profit),
        "outstanding_receivables": str(summary.outstanding_receivables),
    }


async def _handle_list_outstanding_sales(uow: AppUnitOfWork, business_id: uuid.UUID) -> dict[str, Any]:
    sales = await ListOutstandingSalesUseCase(uow).execute(ListOutstandingSalesQuery(business_id=business_id))
    return {
        "sales": [
            {
                "invoice_number": sale.invoice_number,
                "due_date": sale.due_date.isoformat() if sale.due_date else None,
                "outstanding_amount": str(sale.outstanding_amount.amount),
                "payment_status": sale.payment_status.value,
            }
            for sale in sales
        ]
    }


async def _handle_list_outstanding_purchases(uow: AppUnitOfWork, business_id: uuid.UUID) -> dict[str, Any]:
    purchases = await ListOutstandingPurchasesUseCase(uow).execute(
        ListOutstandingPurchasesQuery(business_id=business_id)
    )
    return {
        "purchases": [
            {
                "purchase_number": purchase.purchase_number,
                "due_date": purchase.due_date.isoformat() if purchase.due_date else None,
                "outstanding_amount": str(purchase.outstanding_amount.amount),
                "payment_status": purchase.payment_status.value,
            }
            for purchase in purchases
        ]
    }


async def _handle_list_low_stock_products(uow: AppUnitOfWork, business_id: uuid.UUID) -> dict[str, Any]:
    # PageRequest caps limit at 200 (shared/application/pagination.py) —
    # unlike Sale/Purchase's list_for_business, which is called with a raw
    # int and no such ceiling, so the "scan everything" trick used for
    # outstanding sales/purchases doesn't apply here.
    page = await ListProductsUseCase(uow).execute(
        ListProductsQuery(business_id=business_id, page=PageRequest(offset=0, limit=200))
    )
    low_stock = [p for p in page.items if p.is_low_stock or p.is_out_of_stock]
    return {
        "products": [
            {
                "name": product.name,
                "sku": product.sku,
                "current_quantity": str(product.current_quantity),
                "minimum_stock_level": str(product.minimum_stock_level),
                "is_out_of_stock": product.is_out_of_stock,
            }
            for product in low_stock
        ]
    }


async def _handle_list_recent_expenses(
    uow: AppUnitOfWork, business_id: uuid.UUID, *, limit: int = 10
) -> dict[str, Any]:
    page = await ListExpensesUseCase(uow).execute(
        ListExpensesQuery(business_id=business_id, page=PageRequest(offset=0, limit=200))
    )
    recent = sorted(page.items, key=lambda e: e.expense_date, reverse=True)[:limit]
    return {
        "expenses": [
            {
                "expense_date": expense.expense_date.isoformat(),
                "category": expense.category,
                "description": expense.description,
                "total_amount": str(expense.total_amount.amount),
            }
            for expense in recent
        ]
    }


async def _handle_list_customers(
    uow: AppUnitOfWork, business_id: uuid.UUID, *, limit: int = 20
) -> dict[str, Any]:
    page = await ListCustomersUseCase(uow).execute(
        ListCustomersQuery(business_id=business_id, page=PageRequest(offset=0, limit=limit))
    )
    return {
        "customers": [
            {"name": customer.name, "phone": customer.phone, "email": customer.email}
            for customer in page.items
        ]
    }


TOOL_HANDLERS: dict[str, ToolHandler] = {
    "get_business_summary": _handle_get_business_summary,
    "list_outstanding_sales": _handle_list_outstanding_sales,
    "list_outstanding_purchases": _handle_list_outstanding_purchases,
    "list_low_stock_products": _handle_list_low_stock_products,
    "list_recent_expenses": _handle_list_recent_expenses,
    "list_customers": _handle_list_customers,
}
