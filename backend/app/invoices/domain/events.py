from dataclasses import dataclass

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class InvoiceSubmitted(DomainEvent):
    invoice_number: str
    vendor_id: str
    po_id: str
    total_amount_cents: int


@dataclass(frozen=True, kw_only=True)
class InvoiceMatched(DomainEvent):
    po_id: str


@dataclass(frozen=True, kw_only=True)
class MatchExceptionRaised(DomainEvent):
    po_id: str
    discrepancies: list[str]


@dataclass(frozen=True, kw_only=True)
class InvoiceApproved(DomainEvent):
    invoice_number: str
    vendor_id: str
    total_amount_cents: int


@dataclass(frozen=True, kw_only=True)
class InvoiceRejected(DomainEvent):
    invoice_number: str
    reason: str
