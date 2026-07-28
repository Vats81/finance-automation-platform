import logging
import smtplib
from email.message import EmailMessage

from app.shared.application.ports import EmailAttachment, IEmailSender

logger = logging.getLogger(__name__)


class ConsoleEmailSender(IEmailSender):
    """Dev fallback: logs the email instead of sending it, so verification
    and password-reset flows are testable end-to-end without real SMTP
    credentials configured — same swap-by-settings idea as AUTH_DEV_MODE.
    """

    async def send(
        self, *, to: str, subject: str, body: str, attachments: list[EmailAttachment] | None = None
    ) -> None:
        attachment_note = (
            f"\nAttachments: {', '.join(a.filename for a in attachments)}" if attachments else ""
        )
        logger.info(
            "=== EMAIL (console sender) ===\nTo: %s\nSubject: %s%s\n\n%s",
            to, subject, attachment_note, body,
        )  # fmt: skip


class SmtpEmailSender(IEmailSender):
    def __init__(self, *, host: str, port: int, username: str, password: str, from_address: str) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from_address = from_address

    async def send(
        self, *, to: str, subject: str, body: str, attachments: list[EmailAttachment] | None = None
    ) -> None:
        message = EmailMessage()
        message["From"] = self._from_address
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        for attachment in attachments or []:
            maintype, _, subtype = attachment.content_type.partition("/")
            message.add_attachment(
                attachment.content, maintype=maintype, subtype=subtype, filename=attachment.filename
            )

        with smtplib.SMTP(self._host, self._port, timeout=10) as client:
            client.starttls()
            if self._username:
                client.login(self._username, self._password)
            client.send_message(message)
