import uuid
from dataclasses import dataclass
from datetime import date

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.dashboard.application.queries.get_business_health_score import (
    GetBusinessHealthScoreQuery,
    GetBusinessHealthScoreUseCase,
)
from app.dashboard.application.queries.get_dashboard_summary import (
    GetDashboardSummaryQuery,
    GetDashboardSummaryUseCase,
)
from app.inventory.application.queries.list_products import ListProductsQuery, ListProductsUseCase
from app.sales.application.queries.list_outstanding_sales import (
    ListOutstandingSalesQuery,
    ListOutstandingSalesUseCase,
)
from app.shared.application.pagination import PageRequest
from app.shared.application.ports import IAiClient, IClock

_SYSTEM_PROMPT = (
    "You are the AI Insights writer for a small business finance app. Given a snapshot of the "
    "business's current numbers, write a short, plain-language summary (3-5 bullet points) — what's "
    "going well and what needs attention. Be specific with the numbers given. Never invent figures "
    "that weren't provided."
)

_FALLBACK_INSIGHTS = "Not enough data to generate insights yet."


@dataclass(frozen=True)
class GenerateInsightsCommand:
    business_id: uuid.UUID


@dataclass(frozen=True)
class GenerateInsightsResult:
    insights: str


class GenerateInsightsUseCase:
    """Pre-fetches a fixed set of relevant data (this month's summary, the
    Business Health Score breakdown, top outstanding sales, low-stock
    products) and makes ONE AI call with it embedded in the prompt —
    unlike AskAssistantUseCase's tool-calling loop, there's nothing left
    for the model to decide to fetch, so a loop would just add cost/
    latency for no benefit.
    """

    def __init__(self, uow: AppUnitOfWork, ai_client: IAiClient, clock: IClock) -> None:
        self._uow = uow
        self._ai_client = ai_client
        self._clock = clock

    async def execute(self, command: GenerateInsightsCommand) -> GenerateInsightsResult:
        today = self._clock.now().date()
        month_start = date(today.year, today.month, 1)

        summary = await GetDashboardSummaryUseCase(self._uow).execute(
            GetDashboardSummaryQuery(business_id=command.business_id, start_date=month_start, end_date=today)
        )
        health = await GetBusinessHealthScoreUseCase(self._uow, self._clock).execute(
            GetBusinessHealthScoreQuery(business_id=command.business_id)
        )
        outstanding_sales = await ListOutstandingSalesUseCase(self._uow).execute(
            ListOutstandingSalesQuery(business_id=command.business_id)
        )
        products_page = await ListProductsUseCase(self._uow).execute(
            ListProductsQuery(business_id=command.business_id, page=PageRequest(offset=0, limit=200))
        )
        low_stock = [p for p in products_page.items if p.is_low_stock or p.is_out_of_stock]

        prompt_lines = [
            f"This month's revenue: ${summary.total_revenue}",
            f"This month's expenses: ${summary.total_expenses}",
            f"This month's net profit: ${summary.net_profit}",
            f"Outstanding receivables (all time): ${summary.outstanding_receivables}",
            f"Business Health Score: {health.overall_score}/100 ({health.label})",
            f"Health score breakdown: {health.breakdown}",
            f"Number of outstanding (unpaid/partial) sales: {len(outstanding_sales)}",
        ]
        if outstanding_sales:
            top = outstanding_sales[:3]
            prompt_lines.append(
                "Top outstanding sales: "
                + "; ".join(f"{s.invoice_number} owes ${s.outstanding_amount.amount}" for s in top)
            )
        prompt_lines.append(f"Number of low-stock or out-of-stock products: {len(low_stock)}")
        if low_stock:
            prompt_lines.append("Low-stock products: " + ", ".join(p.name for p in low_stock[:5]))

        response = await self._ai_client.send(
            system=_SYSTEM_PROMPT, messages=[{"role": "user", "content": "\n".join(prompt_lines)}], tools=[]
        )

        return GenerateInsightsResult(insights=response.text or _FALLBACK_INSIGHTS)
