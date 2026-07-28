from dataclasses import dataclass

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ExpenseRecorded(DomainEvent):
    business_id: str
    category: str
    total_amount_cents: int


@dataclass(frozen=True, kw_only=True)
class ExpenseDetailsUpdated(DomainEvent):
    changed_fields: list[str]


@dataclass(frozen=True, kw_only=True)
class ExpenseVoided(DomainEvent):
    category: str
