import base64
import logging
import smtplib
from email.message import EmailMessage

import httpx

from app.shared.application.ports import EmailAttachment, IEmailSender

logger = logging.getLogger(__name__)

_RESEND_API_URL = "https://api.resend.com/emails"


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


class ResendApiEmailSender(IEmailSender):
    """Sends via Resend's HTTPS REST API instead of raw SMTP. Several
    free-tier hosts (this app's own Render deployment included) silently
    drop outbound SMTP connections (port 587/465) for anti-spam reasons,
    while outbound HTTPS is never blocked — this sidesteps that class of
    problem entirely rather than fighting it. Preferred over
    SmtpEmailSender whenever RESEND_API_KEY is set (see
    bootstrap/container.py:get_email_sender).
    """

    def __init__(self, *, api_key: str, from_address: str) -> None:
        self._api_key = api_key
        self._from_address = from_address

    async def send(
        self, *, to: str, subject: str, body: str, attachments: list[EmailAttachment] | None = None
    ) -> None:
        payload: dict = {
            "from": self._from_address,
            "to": [to],
            "subject": subject,
            "text": body,
        }
        if attachments:
            payload["attachments"] = [
                {"filename": a.filename, "content": base64.b64encode(a.content).decode()}
                for a in attachments
            ]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                _RESEND_API_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
