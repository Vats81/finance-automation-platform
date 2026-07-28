import uuid
from datetime import datetime

from pydantic import BaseModel

from app.admin.application.queries.get_platform_stats import PlatformStats
from app.admin.application.queries.list_businesses_overview import (
    BusinessesOverviewPage,
    BusinessOverviewItem,
)
from app.admin.application.queries.list_users_overview import UserOverviewItem, UsersOverviewPage
from app.business.domain.value_objects import BusinessPlan, BusinessStatus


class BusinessOverviewResponse(BaseModel):
    id: uuid.UUID
    name: str
    plan: BusinessPlan
    status: BusinessStatus
    member_count: int
    owner_email: str
    created_at: datetime

    @classmethod
    def from_domain(cls, item: BusinessOverviewItem) -> "BusinessOverviewResponse":
        return cls(
            id=item.id,
            name=item.name,
            plan=item.plan,
            status=item.status,
            member_count=item.member_count,
            owner_email=item.owner_email,
            created_at=item.created_at,
        )


class BusinessesOverviewResponse(BaseModel):
    items: list[BusinessOverviewResponse]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_domain(cls, page: BusinessesOverviewPage) -> "BusinessesOverviewResponse":
        return cls(
            items=[BusinessOverviewResponse.from_domain(i) for i in page.items],
            total=page.total,
            offset=page.offset,
            limit=page.limit,
        )


class UserOverviewResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    is_email_verified: bool
    is_active: bool
    created_at: datetime

    @classmethod
    def from_domain(cls, item: UserOverviewItem) -> "UserOverviewResponse":
        return cls(
            id=item.id,
            email=item.email,
            display_name=item.display_name,
            is_email_verified=item.is_email_verified,
            is_active=item.is_active,
            created_at=item.created_at,
        )


class UsersOverviewResponse(BaseModel):
    items: list[UserOverviewResponse]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_domain(cls, page: UsersOverviewPage) -> "UsersOverviewResponse":
        return cls(
            items=[UserOverviewResponse.from_domain(i) for i in page.items],
            total=page.total,
            offset=page.offset,
            limit=page.limit,
        )


class PlatformStatsResponse(BaseModel):
    total_businesses: int
    total_users: int
    businesses_by_plan: dict[str, int]
    verified_users: int
    unverified_users: int

    @classmethod
    def from_domain(cls, stats: PlatformStats) -> "PlatformStatsResponse":
        return cls(
            total_businesses=stats.total_businesses,
            total_users=stats.total_users,
            businesses_by_plan=stats.businesses_by_plan,
            verified_users=stats.verified_users,
            unverified_users=stats.unverified_users,
        )
