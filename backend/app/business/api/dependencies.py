import uuid
from collections.abc import Callable

from fastapi import Depends, Request

from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.domain.exceptions import BusinessSuspendedException, NotABusinessMemberException
from app.business.domain.value_objects import BusinessRole, BusinessStatus
from app.identity.api.dependencies import get_current_local_user
from app.identity.domain.entities import User
from app.shared.domain.exceptions import UnauthorizedDomainActionException


def require_business_role(*roles: BusinessRole) -> Callable:
    """Dependency factory mirroring identity/api/dependencies.py:require_role,
    but additionally resolves the acting business from the route's
    `business_id` path parameter (FastAPI matches this dependency's
    `business_id` argument to the path param of the same name on any route
    it's used with) and checks the caller's BusinessMembership for that
    business. Passing no roles just requires *some* active membership,
    regardless of role — used by read routes any member may access.
    """

    async def checker(
        request: Request,
        business_id: uuid.UUID,
        current_user: User = Depends(get_current_local_user),
        uow: AppUnitOfWork = Depends(get_uow),
    ) -> User:
        membership = await uow.business_memberships.get_for_user_and_business(
            user_id=current_user.id, business_id=business_id
        )
        if membership is None or not membership.is_active:
            raise NotABusinessMemberException(
                f"User {current_user.id} is not a member of business {business_id}"
            )
        if roles and membership.role not in roles:
            raise UnauthorizedDomainActionException(
                f"Action requires one of roles: {[r.value for r in roles]}"
            )
        # Checked after membership so a non-member can't probe which business
        # ids exist or are suspended. Read on every request, so a suspension
        # (or reactivation) takes effect on the very next call.
        business = await uow.businesses.get_by_id(business_id)
        if business is None or business.status == BusinessStatus.SUSPENDED:
            raise BusinessSuspendedException("This business is suspended. Contact support to restore access.")
        # Read by the audit middleware once the response status is known.
        request.state.audit_actor_id = current_user.id
        request.state.audit_business_id = business_id
        request.state.audit_role = membership.role.value
        return current_user

    # Introspected by tests/unit/api/test_route_permissions.py, which fails if
    # a business-scoped route has no role check at all (deny by default).
    checker.allowed_roles = roles  # type: ignore[attr-defined]
    return checker
