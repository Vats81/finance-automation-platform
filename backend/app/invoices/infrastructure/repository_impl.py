import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.invoices.domain.entities import Invoice
from app.invoices.domain.exceptions import InvoiceNotFoundException
from app.invoices.domain.repository import IInvoiceRepository
from app.invoices.infrastructure.mappers import (
    apply_domain_to_existing_model,
    domain_to_model,
    model_to_domain,
)
from app.invoices.infrastructure.models import InvoiceModel
from app.shared.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemyInvoiceRepository(IInvoiceRepository):
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> AsyncSession:
        return self._uow.session

    async def get_by_id(self, invoice_id: uuid.UUID) -> Invoice | None:
        model = await self._session.get(InvoiceModel, invoice_id)
        return model_to_domain(model) if model else None

    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[Invoice], int]:
        count_result = await self._session.execute(select(func.count()).select_from(InvoiceModel))
        total = count_result.scalar_one()
        stmt = (
            select(InvoiceModel).order_by(InvoiceModel.created_at.desc()).offset(offset).limit(limit)
        )
        result = await self._session.execute(stmt)
        invoices = [model_to_domain(m) for m in result.scalars().all()]
        return invoices, total

    def add(self, invoice: Invoice) -> None:
        self._session.add(domain_to_model(invoice))
        self._uow.collect_events(invoice)

    async def update(self, invoice: Invoice) -> None:
        model = await self._session.get(InvoiceModel, invoice.id)
        if model is None:
            raise InvoiceNotFoundException(f"Invoice {invoice.id} not found")
        apply_domain_to_existing_model(invoice, model)
        self._uow.collect_events(invoice)
