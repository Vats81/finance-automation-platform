from dataclasses import dataclass

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PurchaseOrderCreated(DomainEvent):
    po_number: str
    vendor_id: str
    total_amount_cents: int


@dataclass(frozen=True, kw_only=True)
class PurchaseOrderClosed(DomainEvent):
    po_number: str


@dataclass(frozen=True, kw_only=True)
class PurchaseOrderCancelled(DomainEvent):
    po_number: str
