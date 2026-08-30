"""Technical capability ports (Dependency Inversion boundary).

These are capabilities the application layer needs but does not own the
implementation of. Concrete adapters live in shared/infrastructure and
context-specific infrastructure packages, and are wired in only at the
composition root (app/bootstrap/container.py). The application layer
imports only these abstract interfaces, never a concrete adapter or
framework (celery, azure-storage-blob, etc.) directly.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO


class IClock(ABC):
    @abstractmethod
    def now(self) -> datetime: ...


class IEventPublisher(ABC):
    """Publishes domain events to in-process subscribers (used by the outbox relay)."""

    @abstractmethod
    async def publish(self, event) -> None: ...


class IFileStorage(ABC):
    """Abstraction over blob storage (Azure Blob in prod, Azurite in dev)."""

    @abstractmethod
    async def upload(self, *, container: str, blob_name: str, data: BinaryIO, content_type: str) -> str:
        """Uploads a file and returns a storage URI/reference."""
        ...

    @abstractmethod
    async def get_download_url(
        self, *, container: str, blob_name: str, expires_in_seconds: int = 3600
    ) -> str: ...

    @abstractmethod
    async def delete(self, *, container: str, blob_name: str) -> None: ...


class ITaskQueue(ABC):
    """Abstraction over background task submission (Celery in prod)."""

    @abstractmethod
    def enqueue(self, task_name: str, *, kwargs: dict, queue: str = "default") -> str:
        """Enqueues a task by registered name; returns the task/message id."""
        ...


class IPasswordHasher(ABC):
    """Abstraction over password hashing for self-serve (LOCAL) auth users.
    Concrete adapter uses bcrypt (shared/infrastructure/password_hasher.py);
    kept behind a port so use cases never import a hashing library directly.
    """

    @abstractmethod
    def hash(self, plaintext: str) -> str: ...

    @abstractmethod
    def verify(self, plaintext: str, hashed: str) -> bool: ...


@dataclass(frozen=True)
class EmailAttachment:
    filename: str
    content: bytes
    content_type: str


class IEmailSender(ABC):
    """Abstraction over outbound transactional email (verification links,
    password resets, report delivery). ConsoleEmailSender (dev) and
    SmtpEmailSender (real) both live in shared/infrastructure/email_sender.py,
    selected by settings the same way AUTH_DEV_MODE selects the dev JWT
    bypass. `attachments` defaults to None so the two existing verification/
    reset-email call sites (workers/tasks/notification_tasks.py) need no
    changes.
    """

    @abstractmethod
    async def send(
        self, *, to: str, subject: str, body: str, attachments: list[EmailAttachment] | None = None
    ) -> None: ...


class IWhatsAppSender(ABC):
    """Abstraction over outbound WhatsApp messages. Text-only: WhatsApp media
    messages need a publicly-reachable URL for any attached file (unlike
    email, which can carry raw bytes inline), and this product has no public
    file hosting wired up yet — see dashboard/application/send_report_whatsapp.py
    for how a report is summarized as text instead. ConsoleWhatsAppSender
    (dev) and TwilioWhatsAppSender (real) live in
    shared/infrastructure/whatsapp_sender.py, selected by settings the same
    way IEmailSender's two adapters are.
    """

    @abstractmethod
    async def send(self, *, to: str, message: str) -> None: ...


@dataclass(frozen=True)
class AiToolCall:
    id: str
    name: str
    input: dict


@dataclass(frozen=True)
class AiResponse:
    text: str | None
    tool_calls: list[AiToolCall]
    stop_reason: str


class IAiClient(ABC):
    """Abstraction over the AI provider (Anthropic Claude). ConsoleAiClient
    (dev fallback) and AnthropicAiClient (real) live in
    shared/infrastructure/ai_client.py, selected by settings the same way
    IEmailSender's two adapters are. `messages`/`tools` stay as raw dicts
    matching the Anthropic Messages API's own JSON shape (role/content
    messages, JSON-schema tool defs) rather than a deeper abstraction —
    that shape is already reasonably provider-neutral, and only one AI
    provider is planned, so further abstraction would be premature.
    """

    @abstractmethod
    async def send(self, *, system: str, messages: list[dict], tools: list[dict]) -> AiResponse: ...


@dataclass(frozen=True)
class StripeEvent:
    type: str
    data: dict


class IPaymentGateway(ABC):
    """Abstraction over Stripe billing. No Console/no-op fallback exists
    here (unlike IEmailSender/IWhatsAppSender/IAiClient) — there's no
    meaningful fake version of taking payment; instead the frontend hides
    billing UI entirely when settings.stripe_configured is false (see
    integrations/application/queries/get_integration_status.py). The real
    adapter (StripeGateway) lives in shared/infrastructure/stripe_gateway.py.
    Checkout/portal are Stripe's own hosted pages — the app never touches
    card data.
    """

    @abstractmethod
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
        """`client_reference_id` is opaque to this port — the caller
        (StartCheckoutSessionUseCase) packs `f"{business_id}:{plan}"` into
        it so the webhook can resolve both without a second Stripe API
        call or a separate metadata field.

        Returns the checkout URL to redirect the browser to.
        """
        ...

    @abstractmethod
    async def create_billing_portal_session(self, *, customer_id: str, return_url: str) -> str:
        """Returns the Customer Portal URL to redirect the browser to."""
        ...

    @abstractmethod
    def construct_webhook_event(self, *, payload: bytes, signature: str) -> StripeEvent:
        """Verifies the webhook signature and parses the event. Raises on a
        bad/missing signature — callers must not trust an unverified payload.
        """
        ...
