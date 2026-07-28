import uuid
from dataclasses import dataclass

from app.audit.application.ports import AuditUnitOfWork
from app.audit.domain.entities import AuditLogEntry
from app.shared.application.pagination import Page, PageRequest


@dataclass(frozen=True)
class ListAuditLogQuery:
    page: PageRequest
    aggregate_id: uuid.UUID | None = None


class ListAuditLogUseCase:
    def __init__(self, uow: AuditUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListAuditLogQuery) -> Page[AuditLogEntry]:
        if query.aggregate_id is not None:
            entries, total = await self._uow.audit_log.list_for_aggregate(
                query.aggregate_id, offset=query.page.offset, limit=query.page.limit
            )
        else:
            entries, total = await self._uow.audit_log.list_all(
                offset=query.page.offset, limit=query.page.limit
            )
        return Page(items=entries, total=total, offset=query.page.offset, limit=query.page.limit)
