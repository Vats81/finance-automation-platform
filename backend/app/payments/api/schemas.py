import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.payments.application.commands.update_payment_status import PaymentStatusAction
from app.payments.domain.entities import Payment
from app.payments.domain.value_objects import PaymentStatus


class PaymentResponse(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    vendor_id: uuid.UUID
    amount: Decimal
    status: PaymentStatus
    scheduled_date: datetime
    created_at: datetime

    @classmethod
    def from_domain(cls, payment: Payment) -> "PaymentResponse":
        return cls(
            id=payment.id,
            invoice_id=payment.invoice_id,
            vendor_id=payment.vendor_id,
            amount=payment.amount.amount,
            status=payment.status,
            scheduled_date=payment.scheduled_date,
            created_at=payment.created_at,
        )


class PagedPaymentsResponse(BaseModel):
    items: list[PaymentResponse]
    total: int
    offset: int
    limit: int


class UpdatePaymentStatusRequest(BaseModel):
    action: PaymentStatusAction
