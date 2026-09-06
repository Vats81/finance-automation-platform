import base64
import json
from unittest.mock import MagicMock, patch

import httpx

from app.shared.application.ports import EmailAttachment
from app.shared.infrastructure.email_sender import ConsoleEmailSender, ResendApiEmailSender, SmtpEmailSender


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


async def test_resend_api_email_sender_posts_correct_request_without_attachments() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json={"id": "abc123"})

    transport = httpx.MockTransport(handler)
    sender = ResendApiEmailSender(api_key="re_test_key", from_address="noreply@example.com")

    with patch(
        "app.shared.infrastructure.email_sender.httpx.AsyncClient",
        return_value=httpx.AsyncClient(transport=transport),
    ):
        await sender.send(to="jane@example.com", subject="Hello", body="Hi there")

    assert len(captured_requests) == 1
    request = captured_requests[0]
    assert request.url == "https://api.resend.com/emails"
    assert request.headers["authorization"] == "Bearer re_test_key"
    body = json.loads(request.content)
    assert body["from"] == "noreply@example.com"
    assert body["to"] == ["jane@example.com"]
    assert body["subject"] == "Hello"
    assert body["text"] == "Hi there"
    assert "attachments" not in body


async def test_resend_api_email_sender_base64_encodes_attachments() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json={"id": "abc123"})

    transport = httpx.MockTransport(handler)
    sender = ResendApiEmailSender(api_key="re_test_key", from_address="noreply@example.com")

    with patch(
        "app.shared.infrastructure.email_sender.httpx.AsyncClient",
        return_value=httpx.AsyncClient(transport=transport),
    ):
        await sender.send(
            to="jane@example.com",
            subject="Report",
            body="Attached",
            attachments=[
                EmailAttachment(filename="report.pdf", content=b"%PDF-1.4", content_type="application/pdf")
            ],
        )

    body = json.loads(captured_requests[0].content)
    assert body["attachments"] == [
        {"filename": "report.pdf", "content": base64.b64encode(b"%PDF-1.4").decode()}
    ]


async def test_resend_api_email_sender_raises_on_error_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Invalid API key"})

    transport = httpx.MockTransport(handler)
    sender = ResendApiEmailSender(api_key="bad_key", from_address="noreply@example.com")

    with patch(
        "app.shared.infrastructure.email_sender.httpx.AsyncClient",
        return_value=httpx.AsyncClient(transport=transport),
    ):
        try:
            await sender.send(to="jane@example.com", subject="Hello", body="Hi there")
        except httpx.HTTPStatusError:
            pass
        else:
            raise AssertionError("Expected httpx.HTTPStatusError to be raised")
