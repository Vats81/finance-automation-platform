from unittest.mock import MagicMock, patch

from app.shared.application.ports import EmailAttachment
from app.shared.infrastructure.email_sender import ConsoleEmailSender, SmtpEmailSender


async def test_console_email_sender_works_without_attachments() -> None:
    sender = ConsoleEmailSender()

    await sender.send(to="jane@example.com", subject="Hello", body="Hi there")


async def test_console_email_sender_works_with_attachments() -> None:
    sender = ConsoleEmailSender()

    await sender.send(
        to="jane@example.com",
        subject="Hello",
        body="Hi there",
        attachments=[
            EmailAttachment(filename="report.pdf", content=b"%PDF-1.4", content_type="application/pdf")
        ],
    )


async def test_smtp_email_sender_sends_without_attachments() -> None:
    sender = SmtpEmailSender(
        host="smtp.example.com", port=587, username="", password="", from_address="noreply@example.com"
    )
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch("app.shared.infrastructure.email_sender.smtplib.SMTP", return_value=mock_client):
        await sender.send(to="jane@example.com", subject="Hello", body="Hi there")

    mock_client.send_message.assert_called_once()
    sent_message = mock_client.send_message.call_args[0][0]
    assert sent_message["To"] == "jane@example.com"
    assert sent_message["Subject"] == "Hello"
    assert list(sent_message.iter_attachments()) == []


async def test_smtp_email_sender_attaches_files() -> None:
    sender = SmtpEmailSender(
        host="smtp.example.com", port=587, username="", password="", from_address="noreply@example.com"
    )
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch("app.shared.infrastructure.email_sender.smtplib.SMTP", return_value=mock_client):
        await sender.send(
            to="jane@example.com",
            subject="Report",
            body="Attached",
            attachments=[
                EmailAttachment(filename="report.pdf", content=b"%PDF-1.4", content_type="application/pdf")
            ],
        )

    mock_client.send_message.assert_called_once()
    sent_message = mock_client.send_message.call_args[0][0]
    attachments = list(sent_message.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "report.pdf"
    assert attachments[0].get_content_type() == "application/pdf"
