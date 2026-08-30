"""In-memory fakes for the shared application ports (shared/application/ports.py),
so application-layer tests never need a real Celery broker, blob storage
account, or event bus.
"""

from datetime import datetime, timezone
from typing import BinaryIO

from app.shared.application.ports import (
    AiResponse,
    EmailAttachment,
    IAiClient,
    IClock,
    IEmailSender,
    IEventPublisher,
    IFileStorage,
    IPasswordHasher,
    IPaymentGateway,
    ITaskQueue,
    IWhatsAppSender,
    StripeEvent,
)


class FakeEventPublisher(IEventPublisher):
    def __init__(self) -> None:
        self.published: list = []

    async def publish(self, event) -> None:
        self.published.append(event)


class FakeTaskQueue(ITaskQueue):
    def __init__(self) -> None:
        self.enqueued: list[dict] = []

    def enqueue(self, task_name: str, *, kwargs: dict, queue: str = "default") -> str:
        self.enqueued.append({"task_name": task_name, "kwargs": kwargs, "queue": queue})
        return f"fake-task-id-{len(self.enqueued)}"


class FakeFileStorage(IFileStorage):
    def __init__(self) -> None:
        self.uploaded: dict[str, bytes] = {}

    async def upload(self, *, container: str, blob_name: str, data: BinaryIO, content_type: str) -> str:
        key = f"{container}/{blob_name}"
        self.uploaded[key] = data.read()
        return key

    async def get_download_url(
        self, *, container: str, blob_name: str, expires_in_seconds: int = 3600
    ) -> str:
        return f"https://fake-storage.local/{container}/{blob_name}?expires={expires_in_seconds}"

    async def delete(self, *, container: str, blob_name: str) -> None:
        self.uploaded.pop(f"{container}/{blob_name}", None)


class FakeClock(IClock):
    """Controllable clock for testing token-expiry logic — tests advance
    `current` directly rather than sleeping.
    """

    def __init__(self, current: datetime | None = None) -> None:
        self.current = current or datetime.now(timezone.utc)

    def now(self) -> datetime:
        return self.current


class FakePasswordHasher(IPasswordHasher):
    """Reversible, insecure 'hash' (prefixes the plaintext) — fine for tests,
    never used outside tests/fakes.
    """

    def hash(self, plaintext: str) -> str:
        return f"hashed:{plaintext}"

    def verify(self, plaintext: str, hashed: str) -> bool:
        return hashed == f"hashed:{plaintext}"


class FakeEmailSender(IEmailSender):
    """Records every send() call instead of actually sending anything."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(
        self, *, to: str, subject: str, body: str, attachments: list[EmailAttachment] | None = None
    ) -> None:
        self.sent.append({"to": to, "subject": subject, "body": body, "attachments": attachments or []})


class FakeWhatsAppSender(IWhatsAppSender):
    """Records every send() call instead of actually sending anything."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, *, to: str, message: str) -> None:
        self.sent.append({"to": to, "message": message})


class FakeAiClient(IAiClient):
    """Returns a scripted queue of AiResponses instead of calling a real
    model — lets tests drive the tool-calling loop in AskAssistantUseCase
    deterministically (e.g. queue a tool_use response followed by an
    end_turn response).
    """

    def __init__(self, responses: list[AiResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    async def send(self, *, system: str, messages: list[dict], tools: list[dict]) -> AiResponse:
        self.calls.append({"system": system, "messages": messages, "tools": tools})
        if not self._responses:
            raise AssertionError("FakeAiClient ran out of scripted responses")
        return self._responses.pop(0)


class FakePaymentGateway(IPaymentGateway):
    """Records every call instead of hitting real Stripe, and returns a
    scripted StripeEvent from construct_webhook_event() (set via
    `next_event`) so HandleStripeWebhookUseCase tests can drive each event
    type deterministically without a real signed payload.
    """

    def __init__(self) -> None:
        self.checkout_calls: list[dict] = []
        self.portal_calls: list[dict] = []
        self.next_event: StripeEvent | None = None

    async def create_checkout_session(
        self,
        *,
        customer_id: str | None,
        customer_email: str,
        price_id: str,
        client_reference_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        self.checkout_calls.append(
            {
                "customer_id": customer_id,
                "customer_email": customer_email,
                "price_id": price_id,
                "client_reference_id": client_reference_id,
                "success_url": success_url,
                "cancel_url": cancel_url,
            }
        )
        return f"https://checkout.stripe.com/fake/{client_reference_id}"

    async def create_billing_portal_session(self, *, customer_id: str, return_url: str) -> str:
        self.portal_calls.append({"customer_id": customer_id, "return_url": return_url})
        return f"https://billing.stripe.com/fake/{customer_id}"

    def construct_webhook_event(self, *, payload: bytes, signature: str) -> StripeEvent:
        if self.next_event is None:
            raise AssertionError("FakePaymentGateway.next_event was not set before the webhook call")
        return self.next_event
