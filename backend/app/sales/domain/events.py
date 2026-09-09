from dataclasses import dataclass

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class SaleRecorded(DomainEvent):
    business_id: str
    invoice_number: str
    total_amount_cents: int


@dataclass(frozen=True, kw_only=True)
class SalePaymentRecorded(DomainEvent):
    amount_cents: int
    amount_received_cents: int


@dataclass(frozen=True, kw_only=True)
class SaleVoided(DomainEvent):
    invoice_number: str


@dataclass(frozen=True, kw_only=True)
class SaleDetailsUpdated(DomainEvent):
    changed_fields: list[str]
