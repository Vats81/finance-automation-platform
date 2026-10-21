import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.api.rate_limit import limiter
from app.beta_waitlist.application.ports import IWaitlistStore, WaitlistEntry
from app.beta_waitlist.application.use_cases import update_entry
from app.beta_waitlist.domain.status import WaitlistStatus
from app.beta_waitlist.infrastructure.store_impl import SqlAlchemyWaitlistStore
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.identity.api.dependencies import require_platform_admin

# Public: tighter than the general write limit, like the demo-request form.
_WAITLIST_RATE_LIMIT = "10/hour"

router = APIRouter(prefix="/beta-waitlist", tags=["beta-waitlist"])
admin_router = APIRouter(
    prefix="/admin/beta-waitlist", tags=["admin"], dependencies=[Depends(require_platform_admin)]
)


async def get_waitlist_store(uow: AppUnitOfWork = Depends(get_uow)) -> IWaitlistStore:
    return SqlAlchemyWaitlistStore(uow.session)


class JoinWaitlistBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    work_email: EmailStr
    business_name: str | None = Field(default=None, max_length=200)
    business_type: str | None = Field(default=None, max_length=100)
    bookkeeping_method: str | None = Field(default=None, max_length=100)
    reporting_problem: str | None = Field(default=None, max_length=1000)
    weekly_feedback_ok: bool = False
    # The visitor must confirm they understand what this is, and what not to send.
    acknowledged: bool
    # Honeypot, as on the demo-request form.
    website: str | None = Field(default=None, max_length=500)


class JoinWaitlistResponse(BaseModel):
    received: bool = True


class WaitlistEntryResponse(BaseModel):
    id: uuid.UUID
    name: str
    work_email: str
    business_name: str | None
    business_type: str | None
    bookkeeping_method: str | None
    reporting_problem: str | None
    weekly_feedback_ok: bool
    status: WaitlistStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entry(cls, entry: WaitlistEntry) -> "WaitlistEntryResponse":
        return cls(**entry.__dict__)


class UpdateWaitlistEntryBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    status: WaitlistStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)


@router.post("", response_model=JoinWaitlistResponse, status_code=201)
@limiter.limit(_WAITLIST_RATE_LIMIT)
async def join_waitlist(
    request: Request,
    body: JoinWaitlistBody,
    store: IWaitlistStore = Depends(get_waitlist_store),
) -> JoinWaitlistResponse:
    """Registers interest only. Creates no account and grants no access; the
    answer is identical for a new and a returning email, so it cannot be used to
    discover who has signed up.
    """
    if body.website:
        return JoinWaitlistResponse()
    if not body.acknowledged:
        raise HTTPException(
            status_code=422,
            detail="Please confirm you understand this is a private beta and that you will not send bank "
            "details or real financial files.",
        )
    await store.upsert_interest(
        name=body.name,
        work_email=str(body.work_email),
        business_name=body.business_name or None,
        business_type=body.business_type or None,
        bookkeeping_method=body.bookkeeping_method or None,
        reporting_problem=body.reporting_problem or None,
        weekly_feedback_ok=body.weekly_feedback_ok,
    )
    return JoinWaitlistResponse()


@admin_router.get("", response_model=list[WaitlistEntryResponse])
async def list_waitlist(
    limit: int = Query(default=200, ge=1, le=1000), store: IWaitlistStore = Depends(get_waitlist_store)
) -> list[WaitlistEntryResponse]:
    return [WaitlistEntryResponse.from_entry(e) for e in await store.list_all(limit=limit)]


@admin_router.patch("/{entry_id}", response_model=WaitlistEntryResponse)
async def update_waitlist_entry(
    entry_id: uuid.UUID,
    body: UpdateWaitlistEntryBody,
    store: IWaitlistStore = Depends(get_waitlist_store),
) -> WaitlistEntryResponse:
    entry = await update_entry(store, entry_id, status=body.status, notes=body.notes)
    return WaitlistEntryResponse.from_entry(entry)


@admin_router.delete("/{entry_id}", status_code=204)
async def delete_waitlist_entry(
    entry_id: uuid.UUID, store: IWaitlistStore = Depends(get_waitlist_store)
) -> None:
    if not await store.delete(entry_id):
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
