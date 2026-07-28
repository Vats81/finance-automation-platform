import uuid

from fastapi import APIRouter, Depends

from app.audit.api.schemas import AuditLogEntryResponse, PagedAuditLogResponse
from app.audit.application.queries.list_audit_log import ListAuditLogQuery, ListAuditLogUseCase
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.identity.api.dependencies import require_role
from app.identity.domain.entities import User
from app.identity.domain.value_objects import Role
from app.shared.application.pagination import PageRequest

router = APIRouter(prefix="/audit-log", tags=["audit"])

# The audit trail is sensitive cross-cutting data (who did what, when,
# across every context) — restricted to Finance Admins.
require_auditor = require_role(Role.FINANCE_ADMIN)


@router.get("", response_model=PagedAuditLogResponse)
async def list_audit_log(
    offset: int = 0,
    limit: int = 50,
    aggregate_id: uuid.UUID | None = None,
    _actor: User = Depends(require_auditor),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PagedAuditLogResponse:
    use_case = ListAuditLogUseCase(uow)
    page = await use_case.execute(
        ListAuditLogQuery(page=PageRequest(offset=offset, limit=limit), aggregate_id=aggregate_id)
    )
    return PagedAuditLogResponse(
        items=[AuditLogEntryResponse.from_domain(e) for e in page.items],
        total=page.total,
        offset=page.offset,
        limit=page.limit,
    )
