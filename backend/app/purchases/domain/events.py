from dataclasses import dataclass

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PurchaseRecorded(DomainEvent):
    business_id: str
    purchase_number: str
    vendor_id: str
    total_amount_cents: int


@dataclass(frozen=True, kw_only=True)
class PurchasePaymentRecorded(DomainEvent):
    amount_cents: int
    amount_paid_cents: int


@dataclass(frozen=True, kw_only=True)
class PurchaseVoided(DomainEvent):
    purchase_number: str
