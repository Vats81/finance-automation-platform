import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.payments.domain.entities import Payment
from app.payments.domain.exceptions import PaymentNotFoundException
from app.payments.domain.repository import IPaymentRepository
from app.payments.infrastructure.mappers import (
    apply_domain_to_existing_model,
    domain_to_model,
    model_to_domain,
)
from app.payments.infrastructure.models import PaymentModel
from app.shared.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemyPaymentRepository(IPaymentRepository):
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> AsyncSession:
        return self._uow.session

    async def get_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        model = await self._session.get(PaymentModel, payment_id)
        return model_to_domain(model) if model else None

    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[Payment], int]:
        count_result = await self._session.execute(select(func.count()).select_from(PaymentModel))
        total = count_result.scalar_one()
        stmt = select(PaymentModel).order_by(PaymentModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        payments = [model_to_domain(m) for m in result.scalars().all()]
        return payments, total

    def add(self, payment: Payment) -> None:
        self._session.add(domain_to_model(payment))
        self._uow.collect_events(payment)

    async def update(self, payment: Payment) -> None:
        model = await self._session.get(PaymentModel, payment.id)
        if model is None:
            raise PaymentNotFoundException(f"Payment {payment.id} not found")
        apply_domain_to_existing_model(payment, model)
        self._uow.collect_events(payment)
