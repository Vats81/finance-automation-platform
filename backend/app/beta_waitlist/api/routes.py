import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.api.rate_limit import limiter
from app.beta_waitlist.application.ports import IWaitlistStore, WaitlistEntry
from app.beta_waitlist.application.use_cases import build_invitation_draft, send_invitation, update_entry
from app.beta_waitlist.domain.status import WaitlistStatus
from app.beta_waitlist.infrastructure.store_impl import SqlAlchemyWaitlistStore
from app.bootstrap.container import get_email_sender, get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.config.settings import get_settings
from app.identity.api.dependencies import require_platform_admin
from app.shared.application.ports import IEmailSender

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
    invitation_sent_at: datetime | None = None

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


class InvitationDraftResponse(BaseModel):
    to: str
    subject: str
    body: str
    is_firm: bool
    already_sent_at: datetime | None


class SendInvitationBody(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)
    # Set only when the owner knowingly wants to send it a second time.
    resend: bool = False


@admin_router.get("/{entry_id}/invitation-draft", response_model=InvitationDraftResponse)
async def get_invitation_draft(
    entry_id: uuid.UUID, store: IWaitlistStore = Depends(get_waitlist_store)
) -> InvitationDraftResponse:
    """The suggested invitation for this entry, to read and edit. Sends nothing."""
    entry = await store.get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    settings = get_settings()
    draft = build_invitation_draft(
        entry, frontend_base_url=settings.frontend_base_url, support_email=settings.support_email
    )
    return InvitationDraftResponse(
        to=entry.work_email,
        subject=draft.subject,
        body=draft.body,
        is_firm=draft.is_firm,
        already_sent_at=entry.invitation_sent_at,
    )


@admin_router.post("/{entry_id}/send-invitation", response_model=WaitlistEntryResponse)
@limiter.limit("30/hour")
async def send_invitation_email(
    request: Request,
    entry_id: uuid.UUID,
    body: SendInvitationBody,
    store: IWaitlistStore = Depends(get_waitlist_store),
    email_sender: IEmailSender = Depends(get_email_sender),
) -> WaitlistEntryResponse:
    """Emails exactly the subject and body given (the owner has edited and confirmed them) to an entry
    at Invited, with replies going to the support address. Never sends to an address that is not on
    the waitlist.
    """
    entry = await send_invitation(
        store,
        email_sender,
        entry_id=entry_id,
        subject=body.subject.strip(),
        body=body.body.strip(),
        support_email=get_settings().support_email,
        resend=body.resend,
    )
    return WaitlistEntryResponse.from_entry(entry)
