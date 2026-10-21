import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.audit.infrastructure.models import BusinessAuditEventModel
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.api.dependencies import require_business_role
from app.business.api.permissions import CAN_MANAGE_TEAM
from app.identity.domain.entities import User

router = APIRouter(prefix="/businesses/{business_id}/audit-events", tags=["audit"])


class AuditEventResponse(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID
    actor_role: str
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    status_code: int
    occurred_at: datetime


@router.get("", response_model=list[AuditEventResponse])
async def list_business_audit_events(
    business_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=500),
    _actor: User = Depends(require_business_role(*CAN_MANAGE_TEAM)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> list[AuditEventResponse]:
    """Newest first: who changed what in this business. Owner and Admin only."""
    result = await uow.session.execute(
        select(BusinessAuditEventModel)
        .where(BusinessAuditEventModel.business_id == business_id)
        .order_by(BusinessAuditEventModel.occurred_at.desc())
        .limit(limit)
    )
    return [
        AuditEventResponse(
            id=m.id,
            actor_user_id=m.actor_user_id,
            actor_role=m.actor_role,
            action=m.action,
            entity_type=m.entity_type,
            entity_id=m.entity_id,
            status_code=m.status_code,
            occurred_at=m.occurred_at,
        )
        for m in result.scalars().all()
    ]
