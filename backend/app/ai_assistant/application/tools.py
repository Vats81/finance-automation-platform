import uuid
from collections.abc import Awaitable, Callable
from datetime import date
from decimal import Decimal
from typing import Any

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.customers.application.queries.list_customers import ListCustomersQuery, ListCustomersUseCase
from app.dashboard.application.queries.get_dashboard_summary import (
    GetDashboardSummaryQuery,
    GetDashboardSummaryUseCase,
)
from app.expenses.application.queries.list_expenses import ListExpensesQuery, ListExpensesUseCase
from app.expenses.domain.value_objects import ExpenseStatus
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
            "Get total revenue (sales), total expenses, net profit, and outstanding receivables. "
            "These are computed exactly by the system; report them verbatim. If the user does not name a "
            "period, OMIT both dates to get all-time totals (and say the figures are all-time)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Optional ISO date, e.g. 2026-07-01"},
                "end_date": {"type": "string", "description": "Optional ISO date, e.g. 2026-07-31"},
            },
        },
    },
    {
        "name": "get_top_expenses",
        "description": (
            "Get the largest expenses (sorted by amount, computed exactly by the system) and total "
            "spending per category. Use this for 'biggest expense' / 'where does my money go' questions. "
            "Omit the dates for all-time."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "How many top expenses, default 5"},
                "start_date": {"type": "string", "description": "Optional ISO date"},
                "end_date": {"type": "string", "description": "Optional ISO date"},
            },
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
        "description": (
            "List products that are low on stock or out of stock. Also returns total_products: if it is "
            "0 the business has no products yet, which is not the same as inventory being healthy."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_recent_expenses",
        "description": "List the most recently recorded expenses.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "Max number of expenses, default 10"}},
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


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


async def _handle_get_business_summary(
    uow: AppUnitOfWork, business_id: uuid.UUID, *, start_date: str | None = None, end_date: str | None = None
) -> dict[str, Any]:
    summary = await GetDashboardSummaryUseCase(uow).execute(
        GetDashboardSummaryQuery(
            business_id=business_id, start_date=_parse_date(start_date), end_date=_parse_date(end_date)
        )
    )
    return {
        "period": (
            f"{start_date or 'beginning'} to {end_date or 'today'}"
            if (start_date or end_date)
            else "all time"
        ),
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
        # Without this, an empty `products` list can't distinguish "every
        # product is well stocked" from "no products exist yet."
        "total_products": len(page.items),
        "products": [
            {
                "name": product.name,
                "sku": product.sku,
                "current_quantity": str(product.current_quantity),
                "minimum_stock_level": str(product.minimum_stock_level),
                "is_out_of_stock": product.is_out_of_stock,
            }
            for product in low_stock
        ],
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


async def _handle_get_top_expenses(
    uow: AppUnitOfWork,
    business_id: uuid.UUID,
    *,
    limit: int = 5,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    start, end = _parse_date(start_date), _parse_date(end_date)
    expenses, _ = await uow.expenses.list_for_business(business_id, offset=0, limit=10_000)
    live = [
        e
        for e in expenses
        if e.status != ExpenseStatus.VOID
        and (start is None or e.expense_date >= start)
        and (end is None or e.expense_date <= end)
    ]
    ranked = sorted(live, key=lambda e: e.total_amount.amount, reverse=True)
    by_category: dict[str, Decimal] = {}
    for e in live:
        by_category[e.category] = by_category.get(e.category, Decimal("0")) + e.total_amount.amount
    return {
        "period": f"{start_date or 'beginning'} to {end_date or 'today'}"
        if (start_date or end_date)
        else "all time",
        "expense_count": len(live),
        "total_spent": str(sum((e.total_amount.amount for e in live), Decimal("0"))),
        "top_expenses": [
            {
                "expense_date": e.expense_date.isoformat(),
                "category": e.category,
                "description": e.description,
                "total_amount": str(e.total_amount.amount),
            }
            for e in ranked[: max(1, min(limit, 50))]
        ],
        "by_category": [
            {"category": name, "total": str(total)}
            for name, total in sorted(by_category.items(), key=lambda item: item[1], reverse=True)
        ],
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


_DECLARED_ARGS: dict[str, set[str]] = {
    schema["name"]: set(schema["input_schema"].get("properties", {})) for schema in TOOL_SCHEMAS
}


def filter_tool_input(tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    """Drops any argument the tool's schema doesn't declare. Models sometimes
    add plausible-looking extras (e.g. a `limit` on a tool that takes no
    arguments); the handlers are strict about their signatures, so an
    extra turned into a TypeError, burned one of the assistant loop's few
    round trips on an error message, and could end in "I wasn't able to
    finish answering that." Ignoring what the schema never offered is
    harmless — the handler runs with exactly the arguments it defines.
    Unknown tool names pass through untouched (the caller reports those).
    """
    declared = _DECLARED_ARGS.get(tool_name)
    if declared is None:
        return tool_input
    return {key: value for key, value in tool_input.items() if key in declared}


TOOL_HANDLERS: dict[str, ToolHandler] = {
    "get_business_summary": _handle_get_business_summary,
    "list_outstanding_sales": _handle_list_outstanding_sales,
    "list_outstanding_purchases": _handle_list_outstanding_purchases,
    "list_low_stock_products": _handle_list_low_stock_products,
    "list_recent_expenses": _handle_list_recent_expenses,
    "get_top_expenses": _handle_get_top_expenses,
    "list_customers": _handle_list_customers,
}
