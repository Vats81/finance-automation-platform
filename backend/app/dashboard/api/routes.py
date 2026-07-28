import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Response

from app.bootstrap.container import get_clock, get_email_sender, get_uow, get_whatsapp_sender
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.api.dependencies import require_business_role
from app.business.domain.exceptions import BusinessNotFoundException
from app.business.domain.value_objects import BusinessRole
from app.dashboard.api.schemas import (
    BusinessHealthScoreResponse,
    DashboardSummaryResponse,
    DashboardTrendResponse,
    ForecastResponse,
    SendReportEmailRequest,
    SendReportWhatsAppRequest,
)
from app.dashboard.application.pdf_generator import generate_profit_loss_pdf
from app.dashboard.application.queries.get_business_health_score import (
    GetBusinessHealthScoreQuery,
    GetBusinessHealthScoreUseCase,
)
from app.dashboard.application.queries.get_dashboard_summary import (
    GetDashboardSummaryQuery,
    GetDashboardSummaryUseCase,
)
from app.dashboard.application.queries.get_dashboard_trend import (
    GetDashboardTrendQuery,
    GetDashboardTrendUseCase,
)
from app.dashboard.application.queries.get_forecast import GetForecastQuery, GetForecastUseCase
from app.dashboard.application.send_report_email import SendReportEmailCommand, SendReportEmailUseCase
from app.dashboard.application.send_report_whatsapp import (
    SendReportWhatsAppCommand,
    SendReportWhatsAppUseCase,
)
from app.identity.domain.entities import User
from app.shared.application.ports import IClock, IEmailSender, IWhatsAppSender

router = APIRouter(prefix="/businesses/{business_id}/dashboard", tags=["dashboard"])

_can_write = (BusinessRole.OWNER, BusinessRole.ADMIN, BusinessRole.ACCOUNTANT)


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    business_id: uuid.UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> DashboardSummaryResponse:
    use_case = GetDashboardSummaryUseCase(uow)
    summary = await use_case.execute(
        GetDashboardSummaryQuery(business_id=business_id, start_date=start_date, end_date=end_date)
    )
    return DashboardSummaryResponse.from_domain(summary)


@router.get("/trend", response_model=DashboardTrendResponse)
async def get_dashboard_trend(
    business_id: uuid.UUID,
    start_date: date,
    end_date: date,
    granularity: Literal["day", "week", "month"] | None = None,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> DashboardTrendResponse:
    use_case = GetDashboardTrendUseCase(uow)
    trend = await use_case.execute(
        GetDashboardTrendQuery(
            business_id=business_id, start_date=start_date, end_date=end_date, granularity=granularity
        )
    )
    return DashboardTrendResponse.from_domain(trend)


@router.get("/profit-loss-pdf")
async def get_profit_loss_pdf(
    business_id: uuid.UUID,
    start_date: date,
    end_date: date,
    granularity: Literal["day", "week", "month"] | None = None,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> Response:
    business = await uow.businesses.get_by_id(business_id)
    if business is None:
        raise BusinessNotFoundException(f"Business {business_id} not found")

    trend = await GetDashboardTrendUseCase(uow).execute(
        GetDashboardTrendQuery(
            business_id=business_id, start_date=start_date, end_date=end_date, granularity=granularity
        )
    )
    pdf_bytes = generate_profit_loss_pdf(business.name, trend)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="profit-loss-{trend.granularity}.pdf"'},
    )


@router.post("/profit-loss-pdf/email", status_code=204)
async def send_profit_loss_pdf_email(
    business_id: uuid.UUID,
    body: SendReportEmailRequest,
    start_date: date,
    end_date: date,
    granularity: Literal["day", "week", "month"] | None = None,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
    email_sender: IEmailSender = Depends(get_email_sender),
) -> None:
    await SendReportEmailUseCase(uow, email_sender).execute(
        SendReportEmailCommand(
            business_id=business_id,
            recipient_email=body.recipient_email,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
        )
    )


@router.post("/profit-loss-pdf/whatsapp", status_code=204)
async def send_profit_loss_pdf_whatsapp(
    business_id: uuid.UUID,
    body: SendReportWhatsAppRequest,
    start_date: date,
    end_date: date,
    granularity: Literal["day", "week", "month"] | None = None,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
    whatsapp_sender: IWhatsAppSender = Depends(get_whatsapp_sender),
) -> None:
    await SendReportWhatsAppUseCase(uow, whatsapp_sender).execute(
        SendReportWhatsAppCommand(
            business_id=business_id,
            recipient_phone=body.recipient_phone,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
        )
    )


@router.get("/health-score", response_model=BusinessHealthScoreResponse)
async def get_business_health_score(
    business_id: uuid.UUID,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
    clock: IClock = Depends(get_clock),
) -> BusinessHealthScoreResponse:
    score = await GetBusinessHealthScoreUseCase(uow, clock).execute(
        GetBusinessHealthScoreQuery(business_id=business_id)
    )
    return BusinessHealthScoreResponse.from_domain(score)


@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    business_id: uuid.UUID,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
    clock: IClock = Depends(get_clock),
) -> ForecastResponse:
    forecast = await GetForecastUseCase(uow, clock).execute(GetForecastQuery(business_id=business_id))
    return ForecastResponse.from_domain(forecast)
