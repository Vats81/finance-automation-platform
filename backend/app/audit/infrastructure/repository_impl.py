import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.domain.entities import AuditLogEntry
from app.audit.domain.repository import IAuditLogRepository
from app.audit.infrastructure.models import AuditLogEntryModel
from app.shared.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


def _model_to_domain(model: AuditLogEntryModel) -> AuditLogEntry:
    return AuditLogEntry(
        id=model.id,
        event_type=model.event_type,
        aggregate_id=model.aggregate_id,
        payload=model.payload,
        occurred_at=model.occurred_at,
        recorded_at=model.recorded_at,
    )


class SqlAlchemyAuditLogRepository(IAuditLogRepository):
    """No `collect_events` call in `add()` — AuditLogEntry isn't an
    AggregateRoot and never raises further domain events (that would risk
    infinite audit-of-audit recursion through the outbox).
    """

    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> AsyncSession:
        return self._uow.session

    def add(self, entry: AuditLogEntry) -> None:
        self._session.add(
            AuditLogEntryModel(
                id=entry.id,
                event_type=entry.event_type,
                aggregate_id=entry.aggregate_id,
                payload=entry.payload,
                occurred_at=entry.occurred_at,
                recorded_at=entry.recorded_at,
            )
        )

    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[AuditLogEntry], int]:
        count_result = await self._session.execute(select(func.count()).select_from(AuditLogEntryModel))
        total = count_result.scalar_one()
        stmt = (
            select(AuditLogEntryModel).order_by(AuditLogEntryModel.occurred_at.desc()).offset(offset).limit(limit)
        )
        result = await self._session.execute(stmt)
        entries = [_model_to_domain(m) for m in result.scalars().all()]
        return entries, total

    async def list_for_aggregate(
        self, aggregate_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[AuditLogEntry], int]:
        base_filter = AuditLogEntryModel.aggregate_id == aggregate_id
        count_result = await self._session.execute(
            select(func.count()).select_from(AuditLogEntryModel).where(base_filter)
        )
        total = count_result.scalar_one()
        stmt = (
            select(AuditLogEntryModel)
            .where(base_filter)
            .order_by(AuditLogEntryModel.occurred_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        entries = [_model_to_domain(m) for m in result.scalars().all()]
        return entries, total
