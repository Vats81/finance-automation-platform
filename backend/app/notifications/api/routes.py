import uuid

from fastapi import APIRouter, Depends

from app.bootstrap.container import get_clock, get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.api.dependencies import require_business_role
from app.identity.domain.entities import User
from app.notifications.api.schemas import NotificationsResponse
from app.notifications.application.queries.list_notifications import (
    GetNotificationsQuery,
    ListNotificationsUseCase,
)
from app.shared.application.ports import IClock

router = APIRouter(prefix="/businesses/{business_id}/notifications", tags=["notifications"])


@router.get("", response_model=NotificationsResponse)
async def get_notifications(
    business_id: uuid.UUID,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
    clock: IClock = Depends(get_clock),
) -> NotificationsResponse:
    notifications = await ListNotificationsUseCase(uow, clock).execute(
        GetNotificationsQuery(business_id=business_id)
    )
    return NotificationsResponse.from_domain(notifications)
