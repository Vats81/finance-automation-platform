import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.domain.exceptions import BusinessNotFoundException
from app.config.settings import get_settings
from app.dashboard.application.queries.get_dashboard_trend import (
    GetDashboardTrendQuery,
    GetDashboardTrendUseCase,
)
from app.shared.application.ports import IWhatsAppSender


@dataclass(frozen=True)
class SendReportWhatsAppCommand:
    business_id: uuid.UUID
    recipient_phone: str
    start_date: date
    end_date: date
    granularity: Literal["day", "week", "month"] | None = None


class SendReportWhatsAppUseCase:
    """Sends a text summary of the Profit & Loss report plus a link back to
    the Reports page — not the PDF itself. WhatsApp media messages need a
    publicly-reachable URL for any attached file (unlike email, which can
    carry raw bytes inline), and this product has no public file hosting
    wired up yet; see IWhatsAppSender's docstring. Runs synchronously
    within the request, same reasoning as SendReportEmailUseCase.
    """

    def __init__(self, uow: AppUnitOfWork, whatsapp_sender: IWhatsAppSender) -> None:
        self._uow = uow
        self._whatsapp_sender = whatsapp_sender

    async def execute(self, command: SendReportWhatsAppCommand) -> None:
        business = await self._uow.businesses.get_by_id(command.business_id)
        if business is None:
            raise BusinessNotFoundException(f"Business {command.business_id} not found")

        trend = await GetDashboardTrendUseCase(self._uow).execute(
            GetDashboardTrendQuery(
                business_id=command.business_id,
                start_date=command.start_date,
                end_date=command.end_date,
                granularity=command.granularity,
            )
        )
        total_revenue = sum((p.revenue for p in trend.points), Decimal("0"))
        total_expenses = sum((p.expenses for p in trend.points), Decimal("0"))
        net_profit = total_revenue - total_expenses

        settings = get_settings()
        report_link = f"{settings.frontend_base_url}/app/reports"
        message = (
            f"*{business.name}* — Profit & Loss\n"
            f"{command.start_date.isoformat()} to {command.end_date.isoformat()}\n\n"
            f"Revenue: ${total_revenue:,.2f}\n"
            f"Expenses: ${total_expenses:,.2f}\n"
            f"Net Profit: ${net_profit:,.2f}\n\n"
            f"View the full report: {report_link}"
        )

        await self._whatsapp_sender.send(to=command.recipient_phone, message=message)
