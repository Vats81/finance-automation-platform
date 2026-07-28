import uuid
from dataclasses import dataclass

from app.payments.application.ports import PaymentsUnitOfWork
from app.payments.domain.entities import Payment
from app.payments.domain.exceptions import PaymentNotFoundException


@dataclass(frozen=True)
class GetPaymentQuery:
    payment_id: uuid.UUID


class GetPaymentUseCase:
    def __init__(self, uow: PaymentsUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: GetPaymentQuery) -> Payment:
        payment = await self._uow.payments.get_by_id(query.payment_id)
        if payment is None:
            raise PaymentNotFoundException(f"Payment {query.payment_id} not found")
        return payment
