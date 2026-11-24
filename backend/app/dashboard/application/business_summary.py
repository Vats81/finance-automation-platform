import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.domain.entities import Business
from app.business.domain.exceptions import BusinessNotFoundException
from app.dashboard.application.queries.get_dashboard_trend import (
    GetDashboardTrendQuery,
    GetDashboardTrendUseCase,
)
from app.sales.application.queries.get_receivables import GetReceivablesQuery, GetReceivablesUseCase
from app.sales.domain.value_objects import SaleStatus
from app.shared.domain.money_format import format_money

SummaryPeriod = Literal["today", "yesterday", "week"]
SummaryLanguage = Literal["en", "hi"]

_IST = timezone(timedelta(hours=5, minutes=30))
_TOP_DEBTORS = 3
_MAX_SALES_TO_SCAN = 10_000


def business_today(business: Business, now: datetime) -> date:
    """The business's calendar date right now: Indian time for rupee businesses, UTC otherwise."""
    return now.astimezone(_IST if business.currency == "INR" else timezone.utc).date()


_HI_DAYS = ["सोम", "मंगल", "बुध", "गुरु", "शुक्र", "शनि", "रवि"]  # Monday first, like date.weekday()
_HI_MONTHS = ["जन", "फ़र", "मार्च", "अप्रै", "मई", "जून", "जुल", "अग", "सित", "अक्टू", "नव", "दिस"]

# Every piece of fixed text in the message, by language. The figures and names come from the data.
_TEXT = {
    "en": {
        "today": "Today",
        "yesterday": "Yesterday",
        "week": "Last 7 days",
        "to": "to",
        "sales": "Sales",
        "sale": "sale",
        "sales_n": "sales",
        "expenses": "Expenses",
        "profit": "Profit",
        "loss": "Loss",
        "collect": "To collect (udhaar)",
        "more": "and {n} more",
        "nobody": "Nobody owes you anything right now.",
        "walk_in": "Walk-in customers",
        "open": "Open Finverlo",
    },
    "hi": {
        "today": "आज",
        "yesterday": "कल",
        "week": "पिछले 7 दिन",
        "to": "से",
        "sales": "बिक्री",
        "sale": "बिक्री",
        "sales_n": "बिक्री",
        "expenses": "खर्च",
        "profit": "मुनाफ़ा",
        "loss": "घाटा",
        "collect": "वसूलना है (उधार)",
        "more": "और {n} ग्राहक",
        "nobody": "अभी किसी का कुछ बकाया नहीं है।",
        "walk_in": "बिना नाम के ग्राहक",
        "open": "Finverlo खोलें",
    },
}


def _day(value: date, lang: SummaryLanguage) -> str:
    if lang == "hi":
        return f"{_HI_DAYS[value.weekday()]} {value.day} {_HI_MONTHS[value.month - 1]}"
    return value.strftime("%a %d %b")


def period_range(period: SummaryPeriod, today: date, lang: SummaryLanguage = "en") -> tuple[date, date, str]:
    """The first and last day covered, and how to name it. The week is the seven days before today."""
    words = _TEXT[lang]
    if period == "today":
        return today, today, f"{words['today']} ({_day(today, lang)})"
    if period == "yesterday":
        day = today - timedelta(days=1)
        return day, day, f"{words['yesterday']} ({_day(day, lang)})"
    end = today - timedelta(days=1)
    start = end - timedelta(days=6)
    return start, end, f"{words['week']} ({_day(start, lang)} {words['to']} {_day(end, lang)})"


@dataclass(frozen=True)
class SummaryDebtor:
    name: str | None  # None: sales with no customer attached
    amount: Decimal


@dataclass(frozen=True)
class BusinessSummary:
    business_name: str
    currency: str
    label: str
    start_date: date
    end_date: date
    sales_total: Decimal
    sales_count: int
    expenses_total: Decimal
    profit: Decimal
    to_collect_total: Decimal
    top_debtors: list[SummaryDebtor]
    more_debtors: int


class BuildBusinessSummaryUseCase:
    """The numbers behind the WhatsApp summary: sales, expenses and profit for a period (the same figures the
    Overview shows), plus what customers still owe and who owes the most.
    """

    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, *, business_id: uuid.UUID, period: SummaryPeriod, today: date, lang: SummaryLanguage = "en"
    ) -> BusinessSummary:
        business = await self._uow.businesses.get_by_id(business_id)
        if business is None:
            raise BusinessNotFoundException(f"Business {business_id} not found")
        start, end, label = period_range(period, today, lang)

        trend = await GetDashboardTrendUseCase(self._uow).execute(
            GetDashboardTrendQuery(business_id=business_id, start_date=start, end_date=end, granularity="day")
        )
        sales_total = sum((p.revenue for p in trend.points), Decimal("0"))
        expenses_total = sum((p.expenses for p in trend.points), Decimal("0"))

        sales, _ = await self._uow.sales.list_for_business(business_id, offset=0, limit=_MAX_SALES_TO_SCAN)
        sales_count = sum(1 for s in sales if s.status != SaleStatus.VOID and start <= s.invoice_date <= end)

        owed = await GetReceivablesUseCase(self._uow).execute(
            GetReceivablesQuery(business_id=business_id, today=today)
        )
        customers, _ = await self._uow.customers.list_for_business(business_id, offset=0, limit=10_000)
        names = {c.id: c.name for c in customers}
        debtors = [
            SummaryDebtor(
                name=names.get(g.customer_id) if g.customer_id else None,
                amount=g.outstanding,
            )
            for g in owed
        ]
        return BusinessSummary(
            business_name=business.name,
            currency=business.currency,
            label=label,
            start_date=start,
            end_date=end,
            sales_total=sales_total,
            sales_count=sales_count,
            expenses_total=expenses_total,
            profit=sales_total - expenses_total,
            to_collect_total=sum((d.amount for d in debtors), Decimal("0")),
            top_debtors=debtors[:_TOP_DEBTORS],
            more_debtors=max(0, len(debtors) - _TOP_DEBTORS),
        )


def format_summary_message(summary: BusinessSummary, *, link: str, lang: SummaryLanguage = "en") -> str:
    """The WhatsApp text: bold headings (WhatsApp's *bold*), a few lines, and a link back to the app."""
    words = _TEXT[lang]

    def money(value: Decimal) -> str:
        return format_money(value, summary.currency)

    sales_line = f"{words['sales']}: {money(summary.sales_total)}"
    if summary.sales_count:
        noun = words["sale"] if summary.sales_count == 1 else words["sales_n"]
        sales_line += f" ({summary.sales_count} {noun})"
    result = words["profit"] if summary.profit >= 0 else words["loss"]
    lines = [
        f"*{summary.business_name}* - {summary.label}",
        "",
        sales_line,
        f"{words['expenses']}: {money(summary.expenses_total)}",
        f"{result}: {money(abs(summary.profit))}",
        "",
    ]
    if summary.to_collect_total > 0:
        lines.append(f"*{words['collect']}: {money(summary.to_collect_total)}*")
        lines += [f"- {d.name or words['walk_in']}: {money(d.amount)}" for d in summary.top_debtors]
        if summary.more_debtors:
            lines.append("- " + words["more"].format(n=summary.more_debtors))
    else:
        lines.append(words["nobody"])
    lines += ["", f"{words['open']}: {link}"]
    return "\n".join(lines)
