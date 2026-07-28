from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials

from app.bootstrap.container import get_jwt_validator, get_local_token_validator, get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.identity.api.security import bearer_scheme
from app.identity.application.commands.provision_user import ProvisionUserCommand, ProvisionUserUseCase
from app.identity.domain.entities import User
from app.identity.domain.exceptions import UserDeactivatedException, UserNotFoundException
from app.identity.domain.value_objects import Role
from app.identity.infrastructure.entra.jwt_validator import EntraJwtValidator
from app.identity.infrastructure.local_auth.token_validator import LocalTokenValidator
from app.shared.domain.exceptions import UnauthorizedDomainActionException


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    uow: AppUnitOfWork = Depends(get_uow),
    validator: EntraJwtValidator = Depends(get_jwt_validator),
) -> User:
    """Resource-server auth boundary: validates the bearer token against
    Entra ID's JWKS (or the local dev-mode token format), then JIT-provisions
    /looks up the corresponding local User row, which is the source of truth
    for RBAC (see require_role below).
    """
    claims = await validator.validate(credentials.credentials)
    use_case = ProvisionUserUseCase(uow)
    user = await use_case.execute(
        ProvisionUserCommand(
            entra_object_id=claims.entra_object_id,
            email=claims.email,
            display_name=claims.display_name,
        )
    )
    if not user.is_active:
        raise UserDeactivatedException(f"User {user.id} is deactivated")
    return user


async def get_current_local_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    uow: AppUnitOfWork = Depends(get_uow),
    validator: LocalTokenValidator = Depends(get_local_token_validator),
) -> User:
    """Auth boundary for the SMB Finance Manager product: validates a
    platform-issued (LOCAL) bearer JWT and loads the corresponding User row
    directly by id — no JIT provisioning, since local users are created
    explicitly via /auth/register. Entirely separate from get_current_user
    above, which remains the AP-automation product's Entra-only path.
    """
    user_id = validator.validate(credentials.credentials)
    user = await uow.users.get_by_id(user_id)
    if user is None:
        raise UserNotFoundException(f"User {user_id} not found")
    if not user.is_active:
        raise UserDeactivatedException(f"User {user.id} is deactivated")
    return user


def require_role(*roles: Role) -> Callable[[User], User]:
    """Dependency factory: `Depends(require_role(Role.FINANCE_ADMIN))`.

    This is the HTTP-boundary RBAC check. Domain methods that are also
    reachable from non-HTTP callers (e.g. Celery tasks) additionally
    re-check the actor's role themselves for defense-in-depth — see
    approvals/domain/entities.py ApprovalStep.approve().
    """

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.has_role(*roles):
            raise UnauthorizedDomainActionException(
                f"Action requires one of roles: {[r.value for r in roles]}"
            )
        return current_user

    return checker


async def require_platform_admin(current_user: User = Depends(get_current_local_user)) -> User:
    """Auth boundary for the platform Admin Panel — checks the
    is_platform_admin flag rather than any BusinessRole (which is scoped
    per business membership) or the AP-automation product's Role enum.
    """
    if not current_user.is_platform_admin:
        raise UnauthorizedDomainActionException("Action requires platform admin access")
    return current_user
