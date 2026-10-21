import uuid

from app.beta_waitlist.application.ports import IWaitlistStore, WaitlistEntry
from app.beta_waitlist.domain.status import WaitlistStatus, check_transition
from app.shared.domain.exceptions import NotFoundException


class WaitlistEntryNotFoundException(NotFoundException):
    error_code = "waitlist_entry_not_found"


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
