from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.application.unit_of_work import IUnitOfWork
from app.shared.domain.aggregate_root import AggregateRoot
from app.shared.infrastructure.outbox.outbox_writer import write_event_to_outbox


class SqlAlchemyUnitOfWork(IUnitOfWork):
    """Generic UoW: wraps one AsyncSession and the transactional-outbox write.

    Repositories call `collect_events(aggregate)` after `add`/`update` calls
    so that any domain events raised on the aggregate during this unit of
    work are captured. `commit()` flushes those events to the outbox table
    in the same transaction as the state change, then commits once.

    Context-specific repository properties (uow.vendors, uow.invoices, ...)
    are added by app/bootstrap/unit_of_work.py's AppUnitOfWork subclass,
    keeping this shared/infrastructure module free of any dependency on
    individual bounded contexts.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._pending_aggregates: list[AggregateRoot] = []

    def collect_events(self, aggregate: AggregateRoot) -> None:
        self._pending_aggregates.append(aggregate)

    async def commit(self) -> None:
        for aggregate in self._pending_aggregates:
            for event in aggregate.pull_domain_events():
                await write_event_to_outbox(self.session, event)
        self._pending_aggregates.clear()
        await self.session.commit()

    async def rollback(self) -> None:
        self._pending_aggregates.clear()
        await self.session.rollback()
