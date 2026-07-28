import uuid
from collections.abc import Callable

from fastapi import Depends

from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.domain.exceptions import NotABusinessMemberException
from app.business.domain.value_objects import BusinessRole
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
        return current_user

    return checker
