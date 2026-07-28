from dataclasses import dataclass

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class CustomerCreated(DomainEvent):
    name: str
    business_id: str


@dataclass(frozen=True, kw_only=True)
class CustomerDetailsUpdated(DomainEvent):
    changed_fields: list[str]


@dataclass(frozen=True, kw_only=True)
class CustomerDeactivated(DomainEvent):
    name: str
