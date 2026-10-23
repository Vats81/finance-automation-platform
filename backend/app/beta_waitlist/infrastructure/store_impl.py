import uuid

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.beta_waitlist.application.ports import IWaitlistStore, WaitlistEntry
from app.beta_waitlist.domain.status import WaitlistStatus
from app.beta_waitlist.infrastructure.models import BetaWaitlistEntryModel as Model


def _to_entry(m: Model) -> WaitlistEntry:
    return WaitlistEntry(
        id=m.id,
        name=m.name,
        work_email=m.work_email,
        business_name=m.business_name,
        business_type=m.business_type,
        bookkeeping_method=m.bookkeeping_method,
        reporting_problem=m.reporting_problem,
        weekly_feedback_ok=m.weekly_feedback_ok,
        status=WaitlistStatus(m.status),
        notes=m.notes,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlAlchemyWaitlistStore(IWaitlistStore):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_interest(
        self,
        *,
        name: str,
        work_email: str,
        business_name: str | None,
        business_type: str | None,
        bookkeeping_method: str | None,
        reporting_problem: str | None,
        weekly_feedback_ok: bool,
    ) -> WaitlistEntry:
        answers = {
            "name": name,
            "business_name": business_name,
            "business_type": business_type,
            "bookkeeping_method": bookkeeping_method,
            "reporting_problem": reporting_problem,
            "weekly_feedback_ok": weekly_feedback_ok,
        }
        stmt = (
            pg_insert(Model)
            .values(
                id=uuid.uuid4(),
                work_email=work_email.strip().lower(),
                status=WaitlistStatus.INTERESTED.value,
                **answers,
            )
            .on_conflict_do_update(index_elements=["work_email"], set_=answers)
            .returning(Model)
        )
        row = (await self._session.execute(stmt)).scalar_one()
        await self._session.commit()
        return _to_entry(row)

    async def get(self, entry_id: uuid.UUID) -> WaitlistEntry | None:
        row = await self._session.get(Model, entry_id)
        return _to_entry(row) if row else None

    async def get_by_email(self, work_email: str) -> WaitlistEntry | None:
        result = await self._session.execute(
            select(Model).where(Model.work_email == work_email.strip().lower())
        )
        row = result.scalar_one_or_none()
        return _to_entry(row) if row else None

    async def list_all(self, *, limit: int) -> list[WaitlistEntry]:
        result = await self._session.execute(select(Model).order_by(Model.created_at.desc()).limit(limit))
        return [_to_entry(r) for r in result.scalars()]

    async def set_status(
        self, entry_id: uuid.UUID, *, status: WaitlistStatus | None, notes: str | None
    ) -> WaitlistEntry | None:
        row = await self._session.get(Model, entry_id)
        if row is None:
            return None
        if status is not None:
            row.status = status.value
        if notes is not None:
            row.notes = notes or None
        await self._session.commit()
        await self._session.refresh(row)
        return _to_entry(row)

    async def delete(self, entry_id: uuid.UUID) -> bool:
        result = await self._session.execute(delete(Model).where(Model.id == entry_id))
        await self._session.commit()
        return bool(result.rowcount)  # type: ignore[attr-defined]
