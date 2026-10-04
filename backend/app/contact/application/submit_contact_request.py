import logging
from dataclasses import dataclass

from app.contact.application.ports import ContactRequest, IContactRequestStore
from app.shared.application.ports import IEmailSender

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SubmitContactRequestCommand:
    name: str
    email: str
    business_name: str | None = None
    message: str | None = None


def _one_line(value: str) -> str:
    # Collapse any whitespace (including newlines) so visitor-supplied text
    # can't inject extra headers into the notification email's subject.
    return " ".join(value.split())


class SubmitContactRequestUseCase:
    """Saves the request first, then (if an inbox is configured) emails a
    notification. The save is the part that matters: it commits before any
    email is attempted, and a failed or unconfigured email never loses the
    request or surfaces as an error to the visitor — the row is still
    there, flagged notified=False, and shows up in the admin panel. This
    replaces a form that showed "we'll be in touch" and sent nothing.
    """

    def __init__(
        self, store: IContactRequestStore, email_sender: IEmailSender, *, inbox_email: str
    ) -> None:
        self._store = store
        self._email_sender = email_sender
        self._inbox_email = inbox_email.strip()

    async def execute(self, command: SubmitContactRequestCommand) -> ContactRequest:
        request = await self._store.add(
            name=command.name,
            email=command.email,
            business_name=command.business_name,
            message=command.message,
        )

        if not self._inbox_email:
            logger.info("Contact request %s saved; CONTACT_INBOX_EMAIL not set, no email sent.", request.id)
            return request

        body = "\n".join(
            [
                f"Name: {request.name}",
                f"Email: {request.email}",
                f"Business: {request.business_name or '(not given)'}",
                "",
                "Message:",
                request.message or "(none)",
                "",
                f"Request id: {request.id}",
                f"Received: {request.created_at.isoformat()}",
            ]
        )
        try:
            await self._email_sender.send(
                to=self._inbox_email,
                subject=f"New demo request from {_one_line(request.name)}",
                body=body,
            )
            await self._store.mark_notified(request.id)
        except Exception:  # noqa: BLE001 - the request is already saved; email is best-effort
            logger.exception("Contact request %s saved but the notification email failed.", request.id)

        return request
