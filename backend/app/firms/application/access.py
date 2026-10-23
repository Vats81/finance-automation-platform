"""How firm membership turns into access to a client business.

A business managed by a firm (businesses.firm_id) can be reached by the firm's
active staff without being added to the business's own team. Their role in the
business comes from their role in the firm:

    firm owner / admin  -> business admin   (never business owner)
    firm accountant     -> business accountant
    firm viewer         -> business viewer

If someone also has a direct membership in the business, the stronger of the
two applies. This is evaluated on every request, so removing someone from the
firm (or suspending the firm) takes effect on their next call.
"""

import uuid
from dataclasses import dataclass

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.domain.entities import Business
from app.business.domain.value_objects import BusinessRole
from app.firms.domain.value_objects import FirmRole, FirmStatus

_FIRM_TO_BUSINESS: dict[FirmRole, BusinessRole] = {
    FirmRole.OWNER: BusinessRole.ADMIN,
    FirmRole.ADMIN: BusinessRole.ADMIN,
    FirmRole.ACCOUNTANT: BusinessRole.ACCOUNTANT,
    FirmRole.VIEWER: BusinessRole.VIEWER,
}
_RANK: dict[BusinessRole, int] = {
    BusinessRole.VIEWER: 0,
    BusinessRole.ACCOUNTANT: 1,
    BusinessRole.ADMIN: 2,
    BusinessRole.OWNER: 3,
}


@dataclass(frozen=True)
class BusinessAccess:
    role: BusinessRole
    via_firm: bool


def business_role_for_firm_role(role: FirmRole) -> BusinessRole:
    return _FIRM_TO_BUSINESS[role]


def combine(direct: BusinessRole | None, firm: FirmRole | None) -> BusinessAccess | None:
    """The effective access given a direct business role and/or a firm role."""
    from_firm = _FIRM_TO_BUSINESS[firm] if firm is not None else None
    if direct is None and from_firm is None:
        return None
    if direct is None:
        assert from_firm is not None
        return BusinessAccess(role=from_firm, via_firm=True)
    if from_firm is None or _RANK[direct] >= _RANK[from_firm]:
        return BusinessAccess(role=direct, via_firm=False)
    return BusinessAccess(role=from_firm, via_firm=True)


async def firm_role_for(uow: AppUnitOfWork, business: Business | None, user_id: uuid.UUID) -> FirmRole | None:
    """The user's role in the firm that manages this business, if they are an
    active member of an active firm.
    """
    if business is None or business.firm_id is None:
        return None
    firm = await uow.firms.get_firm(business.firm_id)
    if firm is None or firm.status != FirmStatus.ACTIVE:
        return None
    membership = await uow.firms.get_membership(business.firm_id, user_id)
    return membership.role if membership is not None and membership.is_active else None
