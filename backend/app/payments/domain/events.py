from dataclasses import dataclass

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PaymentScheduled(DomainEvent):
    invoice_id: str
    vendor_id: str
    amount_cents: int
    scheduled_date: str


@dataclass(frozen=True, kw_only=True)
class PaymentStatusUpdated(DomainEvent):
    invoice_id: str
    previous_status: str
    new_status: str
