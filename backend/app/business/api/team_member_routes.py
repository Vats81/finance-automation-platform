import uuid

from fastapi import APIRouter, Depends, Request

from app.api.rate_limit import limiter
from app.bootstrap.container import get_email_sender, get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.api.dependencies import require_business_role
from app.business.api.schemas import (
    InviteTeamMemberRequest,
    TeamMemberResponse,
    UpdateTeamMemberRoleRequest,
)
from app.business.application.commands.invite_team_member import (
    InviteTeamMemberCommand,
    InviteTeamMemberUseCase,
)
from app.business.application.commands.remove_team_member import (
    RemoveTeamMemberCommand,
    RemoveTeamMemberUseCase,
)
from app.business.application.commands.update_team_member_role import (
    UpdateTeamMemberRoleCommand,
    UpdateTeamMemberRoleUseCase,
)
from app.business.application.queries.list_team_members import ListTeamMembersQuery, ListTeamMembersUseCase
from app.business.domain.value_objects import BusinessRole
from app.config.settings import get_settings
from app.identity.domain.entities import User
from app.shared.application.ports import IEmailSender

router = APIRouter(prefix="/businesses/{business_id}/team-members", tags=["team-members"])

settings = get_settings()

_can_write = (BusinessRole.OWNER, BusinessRole.ADMIN)


@router.get("", response_model=list[TeamMemberResponse])
async def list_team_members(
    business_id: uuid.UUID,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> list[TeamMemberResponse]:
    views = await ListTeamMembersUseCase(uow).execute(ListTeamMembersQuery(business_id=business_id))
    return [TeamMemberResponse.from_domain(v) for v in views]


@router.post("", response_model=TeamMemberResponse, status_code=201)
@limiter.limit(settings.rate_limit_write)
async def invite_team_member(
    request: Request,
    business_id: uuid.UUID,
    body: InviteTeamMemberRequest,
    actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
    email_sender: IEmailSender = Depends(get_email_sender),
) -> TeamMemberResponse:
    membership = await InviteTeamMemberUseCase(uow, email_sender).execute(
        InviteTeamMemberCommand(
            business_id=business_id, invited_by_user_id=actor.id, email=body.email, role=body.role
        )
    )
    views = await ListTeamMembersUseCase(uow).execute(ListTeamMembersQuery(business_id=business_id))
    view = next(v for v in views if v.membership_id == membership.id)
    return TeamMemberResponse.from_domain(view)


@router.patch("/{membership_id}", response_model=TeamMemberResponse)
@limiter.limit(settings.rate_limit_write)
async def update_team_member_role(
    request: Request,
    business_id: uuid.UUID,
    membership_id: uuid.UUID,
    body: UpdateTeamMemberRoleRequest,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> TeamMemberResponse:
    await UpdateTeamMemberRoleUseCase(uow).execute(
        UpdateTeamMemberRoleCommand(business_id=business_id, membership_id=membership_id, role=body.role)
    )
    views = await ListTeamMembersUseCase(uow).execute(ListTeamMembersQuery(business_id=business_id))
    view = next(v for v in views if v.membership_id == membership_id)
    return TeamMemberResponse.from_domain(view)


@router.post("/{membership_id}/remove", response_model=TeamMemberResponse)
@limiter.limit(settings.rate_limit_write)
async def remove_team_member(
    request: Request,
    business_id: uuid.UUID,
    membership_id: uuid.UUID,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> TeamMemberResponse:
    await RemoveTeamMemberUseCase(uow).execute(
        RemoveTeamMemberCommand(business_id=business_id, membership_id=membership_id)
    )
    views = await ListTeamMembersUseCase(uow).execute(ListTeamMembersQuery(business_id=business_id))
    view = next(v for v in views if v.membership_id == membership_id)
    return TeamMemberResponse.from_domain(view)
