import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.api.schemas import (
    BusinessesOverviewResponse,
    FirmOverviewResponse,
    PlatformStatsResponse,
    UsersOverviewResponse,
)
from app.admin.application.commands.deactivate_user import DeactivateUserCommand, DeactivateUserUseCase
from app.admin.application.commands.delete_user import DeleteUserCommand, DeleteUserUseCase
from app.admin.application.commands.purge_business import PurgeBusinessCommand, PurgeBusinessUseCase
from app.admin.application.commands.purge_firm import PurgeFirmCommand, PurgeFirmUseCase
from app.admin.application.commands.reactivate_business import (
    ReactivateBusinessCommand,
    ReactivateBusinessUseCase,
)
from app.admin.application.commands.reactivate_user import ReactivateUserCommand, ReactivateUserUseCase
from app.admin.application.commands.suspend_business import SuspendBusinessCommand, SuspendBusinessUseCase
from app.admin.application.queries.export_backup import ExportBackupUseCase
from app.admin.application.queries.get_platform_stats import GetPlatformStatsUseCase
from app.admin.application.queries.list_businesses_overview import (
    ListBusinessesOverviewQuery,
    ListBusinessesOverviewUseCase,
)
from app.admin.application.queries.list_firms_overview import ListFirmsOverviewUseCase
from app.admin.application.queries.list_users_overview import (
    ListUsersOverviewQuery,
    ListUsersOverviewUseCase,
)
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.contact.api.dependencies import get_contact_request_store
from app.contact.api.schemas import ContactRequestResponse, ContactRequestsResponse
from app.contact.application.ports import IContactRequestStore
from app.identity.api.dependencies import require_platform_admin
from app.identity.domain.entities import User

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_platform_admin)])


@router.get("/businesses", response_model=BusinessesOverviewResponse)
async def list_businesses_overview(
    offset: int = 0,
    limit: int = 50,
    uow: AppUnitOfWork = Depends(get_uow),
) -> BusinessesOverviewResponse:
    page = await ListBusinessesOverviewUseCase(uow).execute(
        ListBusinessesOverviewQuery(offset=offset, limit=limit)
    )
    return BusinessesOverviewResponse.from_domain(page)


@router.get("/users", response_model=UsersOverviewResponse)
async def list_users_overview(
    offset: int = 0,
    limit: int = 50,
    uow: AppUnitOfWork = Depends(get_uow),
) -> UsersOverviewResponse:
    page = await ListUsersOverviewUseCase(uow).execute(ListUsersOverviewQuery(offset=offset, limit=limit))
    return UsersOverviewResponse.from_domain(page)


@router.get("/stats", response_model=PlatformStatsResponse)
async def get_platform_stats(uow: AppUnitOfWork = Depends(get_uow)) -> PlatformStatsResponse:
    stats = await GetPlatformStatsUseCase(uow).execute()
    return PlatformStatsResponse.from_domain(stats)


@router.post("/businesses/{business_id}/suspend", status_code=204)
async def suspend_business(business_id: uuid.UUID, uow: AppUnitOfWork = Depends(get_uow)) -> None:
    await SuspendBusinessUseCase(uow).execute(SuspendBusinessCommand(business_id=business_id))


@router.post("/businesses/{business_id}/reactivate", status_code=204)
async def reactivate_business(business_id: uuid.UUID, uow: AppUnitOfWork = Depends(get_uow)) -> None:
    await ReactivateBusinessUseCase(uow).execute(ReactivateBusinessCommand(business_id=business_id))


@router.post("/users/{user_id}/deactivate", status_code=204)
async def deactivate_user(
    user_id: uuid.UUID,
    actor: User = Depends(require_platform_admin),
    uow: AppUnitOfWork = Depends(get_uow),
) -> None:
    await DeactivateUserUseCase(uow).execute(DeactivateUserCommand(user_id=user_id, actor_user_id=actor.id))


@router.post("/users/{user_id}/reactivate", status_code=204)
async def reactivate_user(user_id: uuid.UUID, uow: AppUnitOfWork = Depends(get_uow)) -> None:
    await ReactivateUserUseCase(uow).execute(ReactivateUserCommand(user_id=user_id))


@router.get("/contact-requests", response_model=ContactRequestsResponse)
async def list_contact_requests(
    limit: int = Query(default=100, ge=1, le=500),
    store: IContactRequestStore = Depends(get_contact_request_store),
) -> ContactRequestsResponse:
    """Newest-first demo requests submitted from the landing page. This is
    where requests are read when CONTACT_INBOX_EMAIL isn't set (or an email
    failed) — `notified` says whether an email actually went out.
    """
    requests = await store.list_recent(limit=limit)
    return ContactRequestsResponse(items=[ContactRequestResponse.from_domain(r) for r in requests])


@router.delete("/contact-requests/{request_id}", status_code=204)
async def delete_contact_request(
    request_id: uuid.UUID, store: IContactRequestStore = Depends(get_contact_request_store)
) -> None:
    if not await store.delete(request_id):
        raise HTTPException(status_code=404, detail="Contact request not found")


@router.delete("/businesses/{business_id}", status_code=204)
async def purge_business(
    business_id: uuid.UUID,
    confirm_name: str = Query(min_length=1),
    actor: User = Depends(require_platform_admin),
    uow: AppUnitOfWork = Depends(get_uow),
) -> None:
    """Irreversibly deletes a business and all of its data. `confirm_name`
    must equal the business's name exactly.
    """
    session: AsyncSession = uow.session
    await PurgeBusinessUseCase(session).execute(
        PurgeBusinessCommand(business_id=business_id, confirm_name=confirm_name, actor_user_id=actor.id)
    )


@router.get("/firms", response_model=list[FirmOverviewResponse])
async def list_firms_overview(uow: AppUnitOfWork = Depends(get_uow)) -> list[FirmOverviewResponse]:
    session: AsyncSession = uow.session
    return [
        FirmOverviewResponse.model_validate(f, from_attributes=True)
        for f in await ListFirmsOverviewUseCase(session).execute()
    ]


@router.delete("/firms/{firm_id}", status_code=204)
async def purge_firm(
    firm_id: uuid.UUID,
    confirm_name: str = Query(min_length=1),
    actor: User = Depends(require_platform_admin),
    uow: AppUnitOfWork = Depends(get_uow),
) -> None:
    """Irreversibly deletes a firm and its staff memberships. Refused while it still has client
    businesses. `confirm_name` must equal the firm's name exactly.
    """
    session: AsyncSession = uow.session
    await PurgeFirmUseCase(session).execute(
        PurgeFirmCommand(firm_id=firm_id, confirm_name=confirm_name, actor_user_id=actor.id)
    )


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    confirm_email: str = Query(min_length=1),
    actor: User = Depends(require_platform_admin),
    uow: AppUnitOfWork = Depends(get_uow),
) -> None:
    """Irreversibly deletes a user. `confirm_email` must equal their email."""
    session: AsyncSession = uow.session
    await DeleteUserUseCase(session).execute(
        DeleteUserCommand(user_id=user_id, confirm_email=confirm_email, actor_user_id=actor.id)
    )


@router.get("/backup")
async def export_backup(uow: AppUnitOfWork = Depends(get_uow)) -> Response:
    """A logical (JSON, not SQL-dump) backup of every SMB table — see
    ExportBackupUseCase's docstring for why. A platform admin can call this
    ad hoc; it is also called on a daily schedule by the
    `.github/workflows/backup.yml` GitHub Action, which encrypts the result
    and keeps it as an artifact (no always-on scheduler runs in the app
    itself — Celery Beat is deliberately not deployed here).
    """
    backup = await ExportBackupUseCase(uow.session).execute()
    filename = f"backup-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    return Response(
        content=json.dumps(backup, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
