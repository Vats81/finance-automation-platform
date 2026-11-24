import logging
from dataclasses import dataclass
from datetime import date, datetime

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.domain.entities import Business
from app.dashboard.application.business_summary import (
    BuildBusinessSummaryUseCase,
    SummaryLanguage,
    SummaryPeriod,
    business_today,
    format_summary_message,
)
from app.shared.application.ports import IWhatsAppSender
from app.shared.domain.phone import whatsapp_number

logger = logging.getLogger(__name__)

_MONDAY = 0
_TUESDAY = 1


@dataclass(frozen=True)
class SummaryRunResult:
    sent: int = 0
    skipped: int = 0
    failed: int = 0


def summary_due(business: Business, today: date) -> SummaryPeriod | None:
    """Which summary (if any) this business should get today. Daily businesses get yesterday's every morning;
    weekly ones get the last seven days on Monday (or Tuesday, if Monday's run was missed). A summary is never
    sent twice for the same day, so a late or repeated run is harmless.
    """
    last = business.summary_last_sent_on
    if business.summary_frequency == "daily":
        return "yesterday" if last is None or last < today else None
    if business.summary_frequency == "weekly":
        recent = last is not None and (today - last).days < 6
        return "week" if today.weekday() in (_MONDAY, _TUESDAY) and not recent else None
    return None


class SendDueSummariesUseCase:
    """Sends the WhatsApp summary to every business that asked for one and is due. Meant to be called once a
    day by a scheduler (see .github/workflows/send-summaries.yml); one business failing never stops the rest.
    """

    def __init__(self, uow: AppUnitOfWork, whatsapp_sender: IWhatsAppSender, *, app_link: str) -> None:
        self._uow = uow
        self._sender = whatsapp_sender
        self._link = app_link

    async def execute(self, now: datetime) -> SummaryRunResult:
        sent = skipped = failed = 0
        businesses = await self._uow.businesses.list_with_summary_frequency(("daily", "weekly"))
        for business in businesses:
            today = business_today(business, now)
            period = summary_due(business, today)
            to = whatsapp_number(business.whatsapp_number, business.currency)
            lang: SummaryLanguage = "hi" if business.language == "hi" else "en"
            if period is None or to is None:
                skipped += 1
                continue
            try:
                summary = await BuildBusinessSummaryUseCase(self._uow).execute(
                    business_id=business.id, period=period, today=today, lang=lang
                )
                await self._sender.send(
                    to=to, message=format_summary_message(summary, link=self._link, lang=lang)
                )
                business.summary_last_sent_on = today
                await self._uow.businesses.update(business)
                await self._uow.commit()
                sent += 1
            except Exception:
                logger.exception("Could not send the WhatsApp summary for business %s", business.id)
                await self._uow.rollback()
                failed += 1
        return SummaryRunResult(sent=sent, skipped=skipped, failed=failed)
