"""Firm workflows: creating a firm, managing its staff, and managing the client
businesses it looks after.

Cross-context by nature (firms + businesses + users), so these take the
concrete AppUnitOfWork, the same documented exception as dashboard / ai.
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.domain.entities import Business
from app.business.domain.value_objects import BusinessRole, BusinessStatus
from app.dashboard.application.queries.get_dashboard_summary import (
    GetDashboardSummaryQuery,
    GetDashboardSummaryUseCase,
)
from app.firms.application.ports import FirmMemberRecord, FirmRecord
from app.firms.domain.exceptions import (
    CannotChangeOwnFirmRoleException,
    CannotModifyFirmOwnerException,
    ClientHasNoOtherOwnerException,
    FirmClientNotFoundException,
    FirmNotFoundException,
    FirmOwnerRoleNotAssignableException,
    FirmStaffLimitExceededException,
    FirmStaffNotFoundException,
    StaffAlreadyMemberException,
    StaffInviteeNotRegisteredException,
)
from app.firms.domain.value_objects import FirmMembershipStatus, FirmRole

MAX_FIRM_STAFF = 25
MAX_FIRM_NAME = 255


async def create_firm(uow: AppUnitOfWork, *, owner_user_id: uuid.UUID, name: str) -> FirmRecord:
    firm = await uow.firms.create_firm(name=name.strip(), owner_user_id=owner_user_id)
    await uow.commit()
    return firm


@dataclass(frozen=True)
class MyFirm:
    firm: FirmRecord
    role: FirmRole


async def list_my_firms(uow: AppUnitOfWork, *, user_id: uuid.UUID) -> list[MyFirm]:
    out: list[MyFirm] = []
    for membership in await uow.firms.list_active_memberships_for_user(user_id):
        firm = await uow.firms.get_firm(membership.firm_id)
        if firm is not None:
            out.append(MyFirm(firm=firm, role=membership.role))
    return out


async def get_firm_or_404(uow: AppUnitOfWork, firm_id: uuid.UUID) -> FirmRecord:
    firm = await uow.firms.get_firm(firm_id)
    if firm is None:
        raise FirmNotFoundException(f"Firm {firm_id} not found")
    return firm


# ------------------------------------------------------------------- staff


@dataclass(frozen=True)
class StaffView:
    membership: FirmMemberRecord
    email: str
    display_name: str


async def list_staff(uow: AppUnitOfWork, *, firm_id: uuid.UUID) -> list[StaffView]:
    views: list[StaffView] = []
    for member in await uow.firms.list_members(firm_id):
        user = await uow.users.get_by_id(member.user_id)
        if user is not None:
            views.append(StaffView(member, str(user.email), user.display_name))
    return views


async def invite_staff(
    uow: AppUnitOfWork, *, firm_id: uuid.UUID, actor_user_id: uuid.UUID, email: str, role: FirmRole
) -> FirmMemberRecord:
    if role == FirmRole.OWNER:
        raise FirmOwnerRoleNotAssignableException("The Owner role cannot be granted to a staff member.")
    await get_firm_or_404(uow, firm_id)
    members = await uow.firms.list_members(firm_id)
    if sum(1 for m in members if m.is_active) >= MAX_FIRM_STAFF:
        raise FirmStaffLimitExceededException(f"A firm can have up to {MAX_FIRM_STAFF} staff members.")

    invitee = await uow.users.get_by_email(email)
    if invitee is None:
        raise StaffInviteeNotRegisteredException(
            f"No account found for {email}. Ask them to sign up first, then add them by the same email."
        )
    existing = await uow.firms.get_membership(firm_id, invitee.id)
    if existing is not None and existing.is_active:
        raise StaffAlreadyMemberException(f"{email} is already on this firm's staff.")

    if existing is not None:  # a removed member coming back reuses their row (one per person)
        member = await uow.firms.update_member(
            existing.id, role=role, status=FirmMembershipStatus.ACTIVE, invited_by_user_id=actor_user_id
        )
        assert member is not None
    else:
        member = await uow.firms.add_member(
            firm_id=firm_id, user_id=invitee.id, role=role, invited_by_user_id=actor_user_id
        )
    await uow.commit()
    return member


async def _staff_target(uow: AppUnitOfWork, firm_id: uuid.UUID, membership_id: uuid.UUID) -> FirmMemberRecord:
    member = await uow.firms.get_membership_by_id(membership_id)
    if member is None or member.firm_id != firm_id:
        raise FirmStaffNotFoundException(f"Staff member {membership_id} not found")
    return member


async def change_staff_role(
    uow: AppUnitOfWork,
    *,
    firm_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    membership_id: uuid.UUID,
    role: FirmRole,
) -> FirmMemberRecord:
    if role == FirmRole.OWNER:
        raise FirmOwnerRoleNotAssignableException("The Owner role cannot be granted to a staff member.")
    target = await _staff_target(uow, firm_id, membership_id)
    if target.role == FirmRole.OWNER:
        raise CannotModifyFirmOwnerException("The firm owner's role cannot be changed.")
    if target.user_id == actor_user_id:
        raise CannotChangeOwnFirmRoleException("You cannot change your own role.")
    updated = await uow.firms.update_member(membership_id, role=role)
    assert updated is not None
    await uow.commit()
    return updated


async def remove_staff(
    uow: AppUnitOfWork, *, firm_id: uuid.UUID, membership_id: uuid.UUID
) -> FirmMemberRecord:
    target = await _staff_target(uow, firm_id, membership_id)
    if target.role == FirmRole.OWNER:
        raise CannotModifyFirmOwnerException("The firm owner cannot be removed.")
    updated = await uow.firms.update_member(membership_id, status=FirmMembershipStatus.REMOVED)
    assert updated is not None
    await uow.commit()
    return updated


# ----------------------------------------------------------------- clients


async def add_client(
    uow: AppUnitOfWork, *, firm_id: uuid.UUID, actor_user_id: uuid.UUID, name: str
) -> Business:
    """Creates a client business under the firm. The person who creates it is its
    direct owner (so the business always has an accountable owner); the rest of the
    firm's staff reach it through their firm roles.
    """
    await get_firm_or_404(uow, firm_id)
    return await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=actor_user_id, name=name.strip(), firm_id=firm_id)
    )


async def release_client(uow: AppUnitOfWork, *, firm_id: uuid.UUID, business_id: uuid.UUID) -> Business:
    """The client leaves the firm: the business keeps all its data and its own team,
    and the firm's staff lose access. Refused unless someone on the client's side
    (a direct owner or admin who is not just the firm's own people) can keep running it.
    """
    business = await uow.businesses.get_by_id(business_id)
    if business is None or business.firm_id != firm_id:
        raise FirmClientNotFoundException(f"Client {business_id} not found in this firm")

    firm_people = {m.user_id for m in await uow.firms.list_members(firm_id) if m.is_active}
    direct = [m for m in await uow.business_memberships.list_for_business(business_id) if m.is_active]
    has_client_side_owner = any(
        m.user_id not in firm_people and m.role in (BusinessRole.OWNER, BusinessRole.ADMIN) for m in direct
    )
    if not has_client_side_owner:
        raise ClientHasNoOtherOwnerException(
            "Give the client's own owner access to this business first (Settings, then Team), "
            "so they can keep using it after it leaves the firm."
        )
    business.firm_id = None
    await uow.businesses.update(business)
    await uow.commit()
    return business


@dataclass(frozen=True)
class ClientOverview:
    business: Business
    total_revenue: Decimal
    total_expenses: Decimal
    net_profit: Decimal
    outstanding_receivables: Decimal
    last_activity: datetime | None


async def client_overview(
    uow: AppUnitOfWork, *, firm_id: uuid.UUID, start_date: date | None = None, end_date: date | None = None
) -> list[ClientOverview]:
    """One row per client business with its headline numbers. Suspended
    businesses are listed (so the firm sees them) but not summed.
    """
    businesses = await uow.businesses.list_by_firm_id(firm_id)
    activity = await uow.firms.last_activity_by_business([b.id for b in businesses])
    zero = Decimal("0.00")
    rows: list[ClientOverview] = []
    for business in businesses:
        if business.status == BusinessStatus.SUSPENDED:
            rows.append(ClientOverview(business, zero, zero, zero, zero, activity.get(business.id)))
            continue
        summary = await GetDashboardSummaryUseCase(uow).execute(
            GetDashboardSummaryQuery(business_id=business.id, start_date=start_date, end_date=end_date)
        )
        rows.append(
            ClientOverview(
                business=business,
                total_revenue=summary.total_revenue,
                total_expenses=summary.total_expenses,
                net_profit=summary.net_profit,
                outstanding_receivables=summary.outstanding_receivables,
                last_activity=activity.get(business.id),
            )
        )
    return rows
