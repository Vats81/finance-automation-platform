import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.api.rate_limit import limiter
from app.bootstrap.container import get_clock, get_uow, get_whatsapp_sender
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.config.settings import get_settings
from app.dashboard.application.send_due_summaries import SendDueSummariesUseCase
from app.shared.application.ports import IClock, IWhatsAppSender

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)


def get_cron_secret() -> str:
    return get_settings().cron_secret


@router.post("/summaries/send")
@limiter.limit("10/minute")
async def send_due_summaries(
    request: Request,
    x_cron_secret: str | None = Header(default=None),
    cron_secret: str = Depends(get_cron_secret),
    uow: AppUnitOfWork = Depends(get_uow),
    whatsapp_sender: IWhatsAppSender = Depends(get_whatsapp_sender),
    clock: IClock = Depends(get_clock),
) -> dict[str, int]:
    """Called once a day by the scheduler (GitHub Actions). Sends the WhatsApp summaries that are due. Off
    entirely (404) until CRON_SECRET is set, and the secret is compared in constant time.
    """
    if not cron_secret:
        raise HTTPException(status_code=404)
    if not x_cron_secret or not hmac.compare_digest(x_cron_secret.encode(), cron_secret.encode()):
        raise HTTPException(status_code=403)
    link = f"{get_settings().frontend_base_url.rstrip('/')}/app/dashboard"
    result = await SendDueSummariesUseCase(uow, whatsapp_sender, app_link=link).execute(clock.now())
    return {"sent": result.sent, "skipped": result.skipped, "failed": result.failed}
