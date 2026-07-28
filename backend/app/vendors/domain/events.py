from dataclasses import dataclass

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class VendorCreated(DomainEvent):
    legal_name: str
    contact_email: str


@dataclass(frozen=True, kw_only=True)
class VendorW9DocumentUploaded(DomainEvent):
    document_reference: str


@dataclass(frozen=True, kw_only=True)
class VendorActivated(DomainEvent):
    legal_name: str


@dataclass(frozen=True, kw_only=True)
class VendorDeactivated(DomainEvent):
    legal_name: str


@dataclass(frozen=True, kw_only=True)
class VendorDetailsUpdated(DomainEvent):
    changed_fields: list[str]
