import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.payments.application.ports import PaymentsUnitOfWork
from app.payments.domain.entities import Payment
from app.shared.domain.value_objects import Money

PAYMENT_TERMS_DAYS = 30  # NET-30, foundation-slice default (not yet vendor-configurable)


@dataclass(frozen=True)
class SchedulePaymentCommand:
    invoice_id: uuid.UUID
    vendor_id: uuid.UUID
    amount_cents: int


class SchedulePaymentUseCase:
    """Invoked by payments/application/event_handlers.py in reaction to
    InvoiceApproved — never called directly by a user-initiated API request.
    """

    def __init__(self, uow: PaymentsUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: SchedulePaymentCommand) -> Payment:
        scheduled_date = datetime.now(timezone.utc) + timedelta(days=PAYMENT_TERMS_DAYS)
        payment = Payment.schedule(
            invoice_id=command.invoice_id,
            vendor_id=command.vendor_id,
            amount=Money.from_cents(command.amount_cents),
            scheduled_date=scheduled_date,
        )
        self._uow.payments.add(payment)
        await self._uow.commit()
        return payment
