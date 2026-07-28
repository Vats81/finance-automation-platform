from dataclasses import dataclass
from decimal import Decimal

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ProductCreated(DomainEvent):
    business_id: str
    name: str
    sku: str


@dataclass(frozen=True, kw_only=True)
class ProductDetailsUpdated(DomainEvent):
    changed_fields: list[str]


@dataclass(frozen=True, kw_only=True)
class StockAdjusted(DomainEvent):
    delta: Decimal
    new_quantity: Decimal
    reason: str


@dataclass(frozen=True, kw_only=True)
class ProductDeactivated(DomainEvent):
    name: str
