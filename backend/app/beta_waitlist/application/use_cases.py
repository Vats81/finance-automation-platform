import uuid

from app.beta_waitlist.application.ports import IWaitlistStore, WaitlistEntry
from app.beta_waitlist.domain.status import WaitlistStatus, check_transition
from app.shared.domain.exceptions import NotFoundException


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
