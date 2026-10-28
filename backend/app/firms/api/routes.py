import uuid
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select

from app.api.rate_limit import limiter
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.api.schemas import BusinessResponse
from app.business.domain.value_objects import BusinessStatus
from app.config.settings import get_settings
from app.firms.api.permissions import ANY_STAFF, MANAGE_FIRM
from app.firms.application import use_cases
from app.firms.application.ports import FirmMemberRecord, FirmRecord
from app.firms.domain.exceptions import FirmSuspendedException, NotAFirmMemberException
from app.firms.domain.value_objects import FirmMembershipStatus, FirmRole, FirmStatus
from app.firms.infrastructure.models import FirmAuditEventModel
from app.identity.api.dependencies import get_current_local_user
from app.identity.domain.entities import User

router = APIRouter(prefix="/firms", tags=["firms"])
settings = get_settings()


def require_firm_role(*roles: FirmRole) -> Callable:
    """Dependency factory like business `require_business_role`: the caller must
    be an ACTIVE member of an ACTIVE firm (read on every request, so removal or
    suspension applies to their very next call) and, if roles are given, hold
    one of them.
    """

    async def checker(
        request: Request,
        firm_id: uuid.UUID,
        current_user: User = Depends(get_current_local_user),
        uow: AppUnitOfWork = Depends(get_uow),
    ) -> FirmMemberRecord:
        membership = await uow.firms.get_membership(firm_id, current_user.id)
        if membership is None or not membership.is_active:
            raise NotAFirmMemberException(f"User {current_user.id} is not on this firm's staff")
        if roles and membership.role not in roles:
            raise NotAFirmMemberException(f"Action requires one of roles: {[r.value for r in roles]}")
        firm = await uow.firms.get_firm(firm_id)
        if firm is None or firm.status != FirmStatus.ACTIVE:
            raise FirmSuspendedException("This firm is suspended.")
        # Read by the audit middleware once the response status is known.
        request.state.audit_actor_id = current_user.id
        request.state.audit_firm_id = firm_id
        request.state.audit_role = membership.role.value
        return membership

    checker.allowed_roles = roles  # type: ignore[attr-defined]
    return checker


# ---------------------------------------------------------------- schemas


class CreateFirmRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=use_cases.MAX_FIRM_NAME)


class FirmResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: FirmStatus
    my_role: FirmRole
    created_at: datetime

    @classmethod
    def build(cls, firm: FirmRecord, role: FirmRole) -> "FirmResponse":
        return cls(id=firm.id, name=firm.name, status=firm.status, my_role=role, created_at=firm.created_at)


class StaffResponse(BaseModel):
    membership_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    display_name: str
    role: FirmRole
    status: FirmMembershipStatus

    @classmethod
    def build(cls, view: use_cases.StaffView) -> "StaffResponse":
        m = view.membership
        return cls(
            membership_id=m.id,
            user_id=m.user_id,
            email=view.email,
            display_name=view.display_name,
            role=m.role,
            status=m.status,
        )


class InviteStaffRequest(BaseModel):
    email: EmailStr
    role: FirmRole


class UpdateStaffRoleRequest(BaseModel):
    role: FirmRole


class AddClientRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=255)
    currency: str | None = None


class FirmAuditEventResponse(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID
    actor_role: str
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    status_code: int
    occurred_at: datetime


class ClientResponse(BaseModel):
    business: BusinessResponse
    suspended: bool
    total_revenue: Decimal
    total_expenses: Decimal
    net_profit: Decimal
    outstanding_receivables: Decimal
    last_activity: datetime | None

    @classmethod
    def build(cls, row: use_cases.ClientOverview) -> "ClientResponse":
        return cls(
            business=BusinessResponse.from_domain(row.business),
            suspended=row.business.status == BusinessStatus.SUSPENDED,
            total_revenue=row.total_revenue,
            total_expenses=row.total_expenses,
            net_profit=row.net_profit,
            outstanding_receivables=row.outstanding_receivables,
            last_activity=row.last_activity,
        )


# ----------------------------------------------------------------- routes


@router.post("", response_model=FirmResponse, status_code=201)
@limiter.limit(settings.rate_limit_write)
async def create_firm(
    request: Request,
    body: CreateFirmRequest,
    actor: User = Depends(get_current_local_user),
    uow: AppUnitOfWork = Depends(get_uow),
) -> FirmResponse:
    firm = await use_cases.create_firm(uow, owner_user_id=actor.id, name=body.name)
    request.state.audit_actor_id = actor.id
    request.state.audit_firm_id = firm.id
    request.state.audit_role = FirmRole.OWNER.value
    return FirmResponse.build(firm, FirmRole.OWNER)


@router.get("", response_model=list[FirmResponse])
async def list_my_firms(
    actor: User = Depends(get_current_local_user), uow: AppUnitOfWork = Depends(get_uow)
) -> list[FirmResponse]:
    return [FirmResponse.build(f.firm, f.role) for f in await use_cases.list_my_firms(uow, user_id=actor.id)]


@router.get("/{firm_id}", response_model=FirmResponse)
async def get_firm(
    firm_id: uuid.UUID,
    membership: FirmMemberRecord = Depends(require_firm_role(*ANY_STAFF)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> FirmResponse:
    firm = await use_cases.get_firm_or_404(uow, firm_id)
    return FirmResponse.build(firm, membership.role)


@router.get("/{firm_id}/staff", response_model=list[StaffResponse])
async def list_staff(
    firm_id: uuid.UUID,
    _member: FirmMemberRecord = Depends(require_firm_role(*ANY_STAFF)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> list[StaffResponse]:
    return [StaffResponse.build(v) for v in await use_cases.list_staff(uow, firm_id=firm_id)]


async def _staff_response(uow: AppUnitOfWork, firm_id: uuid.UUID, membership_id: uuid.UUID) -> StaffResponse:
    views = await use_cases.list_staff(uow, firm_id=firm_id)
    return StaffResponse.build(next(v for v in views if v.membership.id == membership_id))


@router.post("/{firm_id}/staff", response_model=StaffResponse, status_code=201)
@limiter.limit(settings.rate_limit_write)
async def invite_staff(
    request: Request,
    firm_id: uuid.UUID,
    body: InviteStaffRequest,
    actor_membership: FirmMemberRecord = Depends(require_firm_role(*MANAGE_FIRM)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> StaffResponse:
    member = await use_cases.invite_staff(
        uow, firm_id=firm_id, actor_user_id=actor_membership.user_id, email=str(body.email), role=body.role
    )
    return await _staff_response(uow, firm_id, member.id)


@router.patch("/{firm_id}/staff/{membership_id}", response_model=StaffResponse)
@limiter.limit(settings.rate_limit_write)
async def change_staff_role(
    request: Request,
    firm_id: uuid.UUID,
    membership_id: uuid.UUID,
    body: UpdateStaffRoleRequest,
    actor_membership: FirmMemberRecord = Depends(require_firm_role(*MANAGE_FIRM)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> StaffResponse:
    await use_cases.change_staff_role(
        uow,
        firm_id=firm_id,
        actor_user_id=actor_membership.user_id,
        membership_id=membership_id,
        role=body.role,
    )
    return await _staff_response(uow, firm_id, membership_id)


@router.post("/{firm_id}/staff/{membership_id}/remove", response_model=StaffResponse)
@limiter.limit(settings.rate_limit_write)
async def remove_staff(
    request: Request,
    firm_id: uuid.UUID,
    membership_id: uuid.UUID,
    _actor: FirmMemberRecord = Depends(require_firm_role(*MANAGE_FIRM)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> StaffResponse:
    await use_cases.remove_staff(uow, firm_id=firm_id, membership_id=membership_id)
    return await _staff_response(uow, firm_id, membership_id)


@router.get("/{firm_id}/clients", response_model=list[ClientResponse])
async def list_clients(
    firm_id: uuid.UUID,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    _member: FirmMemberRecord = Depends(require_firm_role(*ANY_STAFF)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> list[ClientResponse]:
    rows = await use_cases.client_overview(uow, firm_id=firm_id, start_date=start_date, end_date=end_date)
    return [ClientResponse.build(r) for r in rows]


@router.post("/{firm_id}/clients", response_model=BusinessResponse, status_code=201)
@limiter.limit(settings.rate_limit_write)
async def add_client(
    request: Request,
    firm_id: uuid.UUID,
    body: AddClientRequest,
    actor_membership: FirmMemberRecord = Depends(require_firm_role(*MANAGE_FIRM)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> BusinessResponse:
    business = await use_cases.add_client(
        uow, firm_id=firm_id, actor_user_id=actor_membership.user_id, name=body.name, currency=body.currency
    )
    return BusinessResponse.from_domain(business)


@router.post("/{firm_id}/clients/{business_id}/release", response_model=BusinessResponse)
@limiter.limit(settings.rate_limit_write)
async def release_client(
    request: Request,
    firm_id: uuid.UUID,
    business_id: uuid.UUID,
    _actor: FirmMemberRecord = Depends(require_firm_role(*MANAGE_FIRM)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> BusinessResponse:
    business = await use_cases.release_client(uow, firm_id=firm_id, business_id=business_id)
    return BusinessResponse.from_domain(business)


@router.get("/{firm_id}/audit-events", response_model=list[FirmAuditEventResponse])
async def list_firm_audit_events(
    firm_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=500),
    _actor: FirmMemberRecord = Depends(require_firm_role(*MANAGE_FIRM)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> list[FirmAuditEventResponse]:
    """Newest first: who changed the firm's staff and clients. Owner and Admin only."""
    result = await uow.session.execute(
        select(FirmAuditEventModel)
        .where(FirmAuditEventModel.firm_id == firm_id)
        .order_by(FirmAuditEventModel.occurred_at.desc())
        .limit(limit)
    )
    return [
        FirmAuditEventResponse(
            id=m.id,
            actor_user_id=m.actor_user_id,
            actor_role=m.actor_role,
            action=m.action,
            entity_type=m.entity_type,
            entity_id=m.entity_id,
            status_code=m.status_code,
            occurred_at=m.occurred_at,
        )
        for m in result.scalars().all()
    ]
