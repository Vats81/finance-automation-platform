import uuid
from datetime import datetime, timezone

from app.payments.domain.events import PaymentScheduled, PaymentStatusUpdated
from app.payments.domain.exceptions import InvalidPaymentStateTransitionException
from app.payments.domain.value_objects import PaymentStatus
from app.shared.domain.aggregate_root import AggregateRoot
from app.shared.domain.value_objects import Money


class Payment(AggregateRoot):
    """Own aggregate, created reactively off InvoiceApproved (see
    payments/application/event_handlers.py) — never created directly via a
    user-initiated command. Status-tracking only in this foundation slice:
    no real bank-rail execution (ACH/wire) — see PHASE2_ROADMAP.md.
    """

    def __init__(
        self,
        *,
        entity_id: uuid.UUID | None = None,
        invoice_id: uuid.UUID,
        vendor_id: uuid.UUID,
        amount: Money,
        scheduled_date: datetime,
        status: PaymentStatus = PaymentStatus.SCHEDULED,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.invoice_id = invoice_id
        self.vendor_id = vendor_id
        self.amount = amount
        self.scheduled_date = scheduled_date
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)

    @classmethod
    def schedule(
        cls, *, invoice_id: uuid.UUID, vendor_id: uuid.UUID, amount: Money, scheduled_date: datetime
    ) -> "Payment":
        payment = cls(
            invoice_id=invoice_id, vendor_id=vendor_id, amount=amount, scheduled_date=scheduled_date
        )
        payment._record_event(
            PaymentScheduled(
                aggregate_id=payment.id,
                invoice_id=str(invoice_id),
                vendor_id=str(vendor_id),
                amount_cents=amount.cents,
                scheduled_date=scheduled_date.isoformat(),
            )
        )
        return payment

    def _transition(self, new_status: PaymentStatus) -> None:
        if self.status != PaymentStatus.SCHEDULED:
            raise InvalidPaymentStateTransitionException(
                f"Payment {self.id} is {self.status.value}, expected {PaymentStatus.SCHEDULED.value}"
            )
        previous = self.status
        self.status = new_status
        self._record_event(
            PaymentStatusUpdated(
                aggregate_id=self.id,
                invoice_id=str(self.invoice_id),
                previous_status=previous.value,
                new_status=new_status.value,
            )
        )

    def mark_paid(self) -> None:
        self._transition(PaymentStatus.PAID)

    def mark_failed(self) -> None:
        self._transition(PaymentStatus.FAILED)

    def cancel(self) -> None:
        self._transition(PaymentStatus.CANCELLED)
