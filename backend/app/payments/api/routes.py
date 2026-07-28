import uuid

from fastapi import APIRouter, Depends, Request

from app.api.rate_limit import limiter
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.config.settings import get_settings
from app.identity.api.dependencies import get_current_user
from app.identity.domain.entities import User
from app.payments.api.dependencies import require_payments_admin
from app.payments.api.schemas import PagedPaymentsResponse, PaymentResponse, UpdatePaymentStatusRequest
from app.payments.application.commands.update_payment_status import (
    UpdatePaymentStatusCommand,
    UpdatePaymentStatusUseCase,
)
from app.payments.application.queries.get_payment import GetPaymentQuery, GetPaymentUseCase
from app.payments.application.queries.list_payments import ListPaymentsQuery, ListPaymentsUseCase
from app.shared.application.pagination import PageRequest

router = APIRouter(prefix="/payments", tags=["payments"])

settings = get_settings()


@router.get("", response_model=PagedPaymentsResponse)
async def list_payments(
    offset: int = 0,
    limit: int = 50,
    _actor: User = Depends(get_current_user),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PagedPaymentsResponse:
    use_case = ListPaymentsUseCase(uow)
    page = await use_case.execute(ListPaymentsQuery(page=PageRequest(offset=offset, limit=limit)))
    return PagedPaymentsResponse(
        items=[PaymentResponse.from_domain(p) for p in page.items],
        total=page.total,
        offset=page.offset,
        limit=page.limit,
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: uuid.UUID,
    _actor: User = Depends(get_current_user),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PaymentResponse:
    use_case = GetPaymentUseCase(uow)
    payment = await use_case.execute(GetPaymentQuery(payment_id=payment_id))
    return PaymentResponse.from_domain(payment)


@router.post("/{payment_id}/status", response_model=PaymentResponse)
@limiter.limit(settings.rate_limit_write)
async def update_payment_status(
    request: Request,
    payment_id: uuid.UUID,
    body: UpdatePaymentStatusRequest,
    _actor: User = Depends(require_payments_admin),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PaymentResponse:
    use_case = UpdatePaymentStatusUseCase(uow)
    payment = await use_case.execute(UpdatePaymentStatusCommand(payment_id=payment_id, action=body.action))
    return PaymentResponse.from_domain(payment)
