import uuid
from dataclasses import dataclass

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class BusinessRegistered(DomainEvent):
    name: str
    owner_user_id: str


@dataclass(frozen=True, kw_only=True)
class BusinessOnboardingCompleted(DomainEvent):
    pass


@dataclass(frozen=True, kw_only=True)
class MembershipCreated(DomainEvent):
    business_id: uuid.UUID
    user_id: str
    role: str


@dataclass(frozen=True, kw_only=True)
class MembershipRemoved(DomainEvent):
    pass


@dataclass(frozen=True, kw_only=True)
class MembershipRoleChanged(DomainEvent):
    old_role: str
    new_role: str


@dataclass(frozen=True, kw_only=True)
class BusinessPlanChanged(DomainEvent):
    old_plan: str
    new_plan: str


@dataclass(frozen=True, kw_only=True)
class BusinessSuspended(DomainEvent):
    pass
