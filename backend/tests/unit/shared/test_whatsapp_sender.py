from unittest.mock import patch

import httpx

from app.shared.infrastructure.whatsapp_sender import ConsoleWhatsAppSender, TwilioWhatsAppSender


async def test_console_whatsapp_sender_works() -> None:
    sender = ConsoleWhatsAppSender()

    await sender.send(to="+15551234567", message="Hello from FinanceAI")


async def test_twilio_whatsapp_sender_posts_correct_request() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(201, json={"sid": "SMxxxx"})

    transport = httpx.MockTransport(handler)

    sender = TwilioWhatsAppSender(account_sid="ACtest", auth_token="secret", from_number="+15550000000")

    with patch(
        "app.shared.infrastructure.whatsapp_sender.httpx.AsyncClient",
        return_value=httpx.AsyncClient(transport=transport),
    ):
        await sender.send(to="+15551234567", message="Your report is ready")

    assert len(captured_requests) == 1
    request = captured_requests[0]
    assert request.url.path == "/2010-04-01/Accounts/ACtest/Messages.json"
    body = request.content.decode()
    assert "Body=Your+report+is+ready" in body
    assert "From=whatsapp%3A%2B15550000000" in body
    assert "To=whatsapp%3A%2B15551234567" in body


async def test_twilio_whatsapp_sender_raises_on_error_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Authenticate"})

    transport = httpx.MockTransport(handler)
    sender = TwilioWhatsAppSender(account_sid="ACtest", auth_token="bad", from_number="+15550000000")

    with patch(
        "app.shared.infrastructure.whatsapp_sender.httpx.AsyncClient",
        return_value=httpx.AsyncClient(transport=transport),
    ):
        try:
            await sender.send(to="+15551234567", message="Hi")
        except httpx.HTTPStatusError:
            pass
        else:
            raise AssertionError("Expected httpx.HTTPStatusError to be raised")
