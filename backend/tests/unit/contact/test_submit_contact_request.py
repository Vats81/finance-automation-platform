import uuid
from datetime import datetime, timezone

from app.contact.application.ports import ContactRequest, IContactRequestStore
from app.contact.application.submit_contact_request import (
    SubmitContactRequestCommand,
    SubmitContactRequestUseCase,
)
from app.shared.application.ports import EmailAttachment, IEmailSender
from tests.fakes.fake_ports import FakeEmailSender


class InMemoryContactRequestStore(IContactRequestStore):
    def __init__(self) -> None:
        self.rows: dict[uuid.UUID, ContactRequest] = {}

    async def add(
        self, *, name: str, email: str, business_name: str | None, message: str | None
    ) -> ContactRequest:
        request = ContactRequest(
            id=uuid.uuid4(),
            name=name,
            email=email,
            business_name=business_name,
            message=message,
            notified=False,
            created_at=datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
        )
        self.rows[request.id] = request
        return request

    async def mark_notified(self, request_id: uuid.UUID) -> None:
        old = self.rows[request_id]
        self.rows[request_id] = ContactRequest(**{**old.__dict__, "notified": True})

    async def list_recent(self, *, limit: int) -> list[ContactRequest]:
        return sorted(self.rows.values(), key=lambda r: r.created_at, reverse=True)[:limit]


class FailingEmailSender(IEmailSender):
    async def send(
        self, *, to: str, subject: str, body: str, attachments: list[EmailAttachment] | None = None
    ) -> None:
        raise RuntimeError("email provider is down")


_COMMAND = SubmitContactRequestCommand(
    name="Asha Rao", email="asha@example.com", business_name="Rao Traders", message="Can we see a demo?"
)


async def test_saves_the_request_then_emails_the_inbox() -> None:
    store = InMemoryContactRequestStore()
    sender = FakeEmailSender()

    use_case = SubmitContactRequestUseCase(store, sender, inbox_email="owner@example.com")
    request = await use_case.execute(_COMMAND)

    assert len(store.rows) == 1
    assert store.rows[request.id].notified is True
    assert len(sender.sent) == 1
    assert sender.sent[0]["to"] == "owner@example.com"
    assert sender.sent[0]["subject"] == "New demo request from Asha Rao"
    assert "asha@example.com" in sender.sent[0]["body"]
    assert "Rao Traders" in sender.sent[0]["body"]
    assert "Can we see a demo?" in sender.sent[0]["body"]


async def test_without_an_inbox_the_request_is_saved_and_nothing_is_emailed() -> None:
    store = InMemoryContactRequestStore()
    sender = FakeEmailSender()

    request = await SubmitContactRequestUseCase(store, sender, inbox_email="").execute(_COMMAND)

    assert len(store.rows) == 1
    assert store.rows[request.id].notified is False
    assert sender.sent == []


async def test_a_failing_email_provider_never_loses_the_request_or_raises() -> None:
    # The whole point of the fix: the old form showed "we'll be in touch"
    # and discarded everything. The request must survive a broken email
    # provider, flagged notified=False so it's findable in the admin panel.
    store = InMemoryContactRequestStore()

    request = await SubmitContactRequestUseCase(
        store, FailingEmailSender(), inbox_email="owner@example.com"
    ).execute(_COMMAND)

    assert len(store.rows) == 1
    assert store.rows[request.id].notified is False


async def test_newlines_in_the_name_cannot_inject_extra_subject_lines() -> None:
    store = InMemoryContactRequestStore()
    sender = FakeEmailSender()

    await SubmitContactRequestUseCase(store, sender, inbox_email="owner@example.com").execute(
        SubmitContactRequestCommand(name="Eve\r\nBcc: attacker@example.com", email="eve@example.com")
    )

    subject = sender.sent[0]["subject"]
    assert "\n" not in subject and "\r" not in subject
    assert subject == "New demo request from Eve Bcc: attacker@example.com"
