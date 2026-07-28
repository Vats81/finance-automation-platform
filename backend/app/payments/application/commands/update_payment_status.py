import uuid
from dataclasses import dataclass
from enum import Enum

from app.payments.application.ports import PaymentsUnitOfWork
from app.payments.domain.entities import Payment
from app.payments.domain.exceptions import PaymentNotFoundException


class PaymentStatusAction(str, Enum):
    MARK_PAID = "mark_paid"
    MARK_FAILED = "mark_failed"
    CANCEL = "cancel"


@dataclass(frozen=True)
class UpdatePaymentStatusCommand:
    payment_id: uuid.UUID
    action: PaymentStatusAction


class UpdatePaymentStatusUseCase:
    """Manual status update (mark paid/failed, cancel) — reachable only via
    the /payments/{id}/status endpoint, gated to Finance Admins. Real bank
    settlement confirmation (Phase 2) would call mark_paid()/mark_failed()
    through a webhook handler instead of this manual path.
    """

    def __init__(self, uow: PaymentsUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: UpdatePaymentStatusCommand) -> Payment:
        payment = await self._uow.payments.get_by_id(command.payment_id)
        if payment is None:
            raise PaymentNotFoundException(f"Payment {command.payment_id} not found")

        if command.action == PaymentStatusAction.MARK_PAID:
            payment.mark_paid()
        elif command.action == PaymentStatusAction.MARK_FAILED:
            payment.mark_failed()
        else:
            payment.cancel()

        await self._uow.payments.update(payment)
        await self._uow.commit()
        return payment
