from typing import Protocol

from app.audit.domain.repository import IAuditLogRepository


class AuditUnitOfWork(Protocol):
    """See identity/application/ports.py for why this Protocol exists and
    why the repo is declared as `@property` rather than a plain attribute.
    """

    @property
    def audit_log(self) -> IAuditLogRepository: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
