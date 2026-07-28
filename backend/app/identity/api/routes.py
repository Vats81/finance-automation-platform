import uuid

from fastapi import APIRouter, Depends, Request

from app.api.rate_limit import limiter
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.config.settings import get_settings
from app.identity.api.dependencies import get_current_user, require_role
from app.identity.api.schemas import AssignRoleRequest, PagedUsersResponse, UserResponse
from app.identity.application.commands.assign_role import AssignRoleCommand, AssignRoleUseCase
from app.identity.application.queries.list_users import ListUsersQuery, ListUsersUseCase
from app.identity.domain.entities import User
from app.identity.domain.value_objects import Role
from app.shared.application.pagination import PageRequest

router = APIRouter(tags=["identity"])

settings = get_settings()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.from_domain(current_user)


@router.get("/users", response_model=PagedUsersResponse)
async def list_users(
    offset: int = 0,
    limit: int = 50,
    _actor: User = Depends(require_role(Role.FINANCE_ADMIN)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PagedUsersResponse:
    use_case = ListUsersUseCase(uow)
    page = await use_case.execute(ListUsersQuery(page=PageRequest(offset=offset, limit=limit)))
    return PagedUsersResponse(
        items=[UserResponse.from_domain(u) for u in page.items],
        total=page.total,
        offset=page.offset,
        limit=page.limit,
    )


@router.post("/users/{user_id}/role", response_model=UserResponse)
@limiter.limit(settings.rate_limit_write)
async def assign_role(
    request: Request,
    user_id: uuid.UUID,
    body: AssignRoleRequest,
    actor: User = Depends(require_role(Role.FINANCE_ADMIN)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> UserResponse:
    use_case = AssignRoleUseCase(uow)
    user = await use_case.execute(
        AssignRoleCommand(target_user_id=user_id, new_role=body.role, actor_user_id=actor.id)
    )
    return UserResponse.from_domain(user)
