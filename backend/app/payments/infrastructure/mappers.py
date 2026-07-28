from app.payments.domain.entities import Payment
from app.payments.domain.value_objects import PaymentStatus
from app.payments.infrastructure.models import PaymentModel
from app.shared.domain.value_objects import Money


def model_to_domain(model: PaymentModel) -> Payment:
    return Payment(
        entity_id=model.id,
        invoice_id=model.invoice_id,
        vendor_id=model.vendor_id,
        amount=Money.from_cents(model.amount_cents),
        scheduled_date=model.scheduled_date,
        status=PaymentStatus(model.status),
        created_at=model.created_at,
    )


def domain_to_model(payment: Payment) -> PaymentModel:
    return PaymentModel(
        id=payment.id,
        invoice_id=payment.invoice_id,
        vendor_id=payment.vendor_id,
        amount_cents=payment.amount.cents,
        status=payment.status.value,
        scheduled_date=payment.scheduled_date,
        created_at=payment.created_at,
    )


def apply_domain_to_existing_model(payment: Payment, model: PaymentModel) -> None:
    model.status = payment.status.value
