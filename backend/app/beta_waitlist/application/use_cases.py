import logging
import uuid
from dataclasses import dataclass

from app.beta_waitlist.application.ports import IWaitlistStore, WaitlistEntry
from app.beta_waitlist.domain.status import WaitlistStatus, check_transition
from app.shared.application.ports import IEmailSender
from app.shared.domain.exceptions import ConflictException, DomainException, NotFoundException

logger = logging.getLogger(__name__)


class WaitlistEntryNotFoundException(NotFoundException):
    error_code = "waitlist_entry_not_found"


_CAN_SIGN_UP = frozenset({WaitlistStatus.INVITED, WaitlistStatus.ONBOARDED})


async def is_invited(store: IWaitlistStore, email: str) -> bool:
    """True if the owner has invited this email (Invited, or already Onboarded)."""
    entry = await store.get_by_email(email)
    return entry is not None and entry.status in _CAN_SIGN_UP


async def mark_onboarded_if_invited(store: IWaitlistStore, email: str) -> None:
    """An invited person who has now created an account is Onboarded."""
    entry = await store.get_by_email(email)
    if entry is not None and entry.status == WaitlistStatus.INVITED:
        await store.set_status(entry.id, status=WaitlistStatus.ONBOARDED, notes=None)


async def update_entry(
    store: IWaitlistStore, entry_id: uuid.UUID, *, status: WaitlistStatus | None, notes: str | None
) -> WaitlistEntry:
    current = await store.get(entry_id)
    if current is None:
        raise WaitlistEntryNotFoundException(f"Waitlist entry {entry_id} not found")
    if status is not None:
        check_transition(current.status, status)
    updated = await store.set_status(entry_id, status=status, notes=notes)
    if updated is None:  # deleted between the read and the write
        raise WaitlistEntryNotFoundException(f"Waitlist entry {entry_id} not found")
    return updated


# ------------------------------------------------------------- the invitation email


class WaitlistEntryNotInvitedException(ConflictException):
    """An invitation email can only go to someone the owner has moved to Invited."""

    error_code = "waitlist_not_invited"


class InvitationAlreadySentException(ConflictException):
    error_code = "invitation_already_sent"


class InvitationEmailFailedException(DomainException):
    """The mail provider refused or could not be reached. Nothing is marked as sent."""

    error_code = "invitation_email_failed"
    http_status = 502


@dataclass(frozen=True)
class InvitationDraft:
    subject: str
    body: str
    is_firm: bool


_FIRM_WORDS = ("firm", "accounting", "accountant", "bookkeep", "cpa", "practice")


def _looks_like_a_firm(entry: WaitlistEntry) -> bool:
    text = f"{entry.business_type or ''} {entry.business_name or ''}".lower()
    return any(word in text for word in _FIRM_WORDS)


def build_invitation_draft(
    entry: WaitlistEntry, *, frontend_base_url: str, support_email: str
) -> InvitationDraft:
    """The suggested message. The owner reads and edits it before anything is sent."""
    first_name = (entry.name.split() or ["there"])[0]
    signup_url = f"{frontend_base_url}/app/signup"
    beta_url = f"{frontend_base_url}/beta"
    is_firm = _looks_like_a_firm(entry)
    who = entry.business_name or ("your firm" if is_firm else "your business")

    if is_firm:
        steps = (
            f'1. Sign up at {signup_url} with this email address ({entry.work_email}), then choose "I run an '
            'accounting or bookkeeping firm".\n'
            "2. Add one client to start: your own books, or one client who has agreed. Import their "
            "spreadsheet and compare the totals with what you already have.\n"
            "3. Invite a colleague if you like (they sign up first, then you add them with their email).\n"
            "4. Keep your existing records, and tell me about anything that doesn't match, however small."
        )
    else:
        steps = (
            f"1. Sign up at {signup_url} with this email address ({entry.work_email}).\n"
            "2. Register your business and import one month of your spreadsheet (a small file is fine).\n"
            "3. Compare the totals with what you already have.\n"
            "4. Keep your existing records, and tell me about anything that doesn't match, however small."
        )
    body = (
        f"Hi {first_name},\n\n"
        f"I'd like to invite {who} to the Finverlo beta. Here is how it will go:\n\n"
        f"{steps}\n\n"
        "It's free during the beta and no payment details are involved. Please don't send bank details "
        f"or real financial files by email. There's a short tester guide at {beta_url}. "
        f"For anything urgent or odd, write to {support_email}.\n\n"
        "Thank you for helping,\n"
        "The Finverlo beta team"
    )
    return InvitationDraft(subject="Your place in the Finverlo beta", body=body, is_firm=is_firm)


async def send_invitation(
    store: IWaitlistStore,
    sender: IEmailSender,
    *,
    entry_id: uuid.UUID,
    subject: str,
    body: str,
    support_email: str,
    resend: bool = False,
) -> WaitlistEntry:
    """Emails the (possibly edited) invitation to an Invited entry and records when. Refuses anyone who
    is not at Invited, and a second send unless the owner says it is a deliberate resend. A provider
    failure sends nothing and marks nothing.
    """
    entry = await store.get(entry_id)
    if entry is None:
        raise WaitlistEntryNotFoundException(f"Waitlist entry {entry_id} not found")
    if entry.status != WaitlistStatus.INVITED:
        raise WaitlistEntryNotInvitedException(
            "Move this entry to Invited before sending the invitation email."
        )
    if entry.invitation_sent_at is not None and not resend:
        raise InvitationAlreadySentException(
            "An invitation was already emailed to this address. Send it again only if you mean to."
        )
    try:
        await sender.send(to=entry.work_email, subject=subject, body=body, reply_to=support_email)
    except Exception as exc:  # noqa: BLE001 - whatever the provider raised, report it plainly
        logger.warning("Invitation email to waitlist entry %s failed: %s", entry_id, exc)
        raise InvitationEmailFailedException(
            "The email could not be sent just now, so nothing was sent. "
            "Check the Resend dashboard, then try again."
        ) from exc
    updated = await store.mark_invitation_sent(entry_id)
    if updated is None:  # deleted between the send and the write: the email did go out
        raise WaitlistEntryNotFoundException(f"Waitlist entry {entry_id} not found")
    return updated
