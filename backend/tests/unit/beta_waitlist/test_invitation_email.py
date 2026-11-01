"""The invitation email: drafted, edited by the owner, then sent only on an explicit confirm."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.beta_waitlist.application.ports import WaitlistEntry
from app.beta_waitlist.application.use_cases import build_invitation_draft
from app.beta_waitlist.domain.status import WaitlistStatus
from app.bootstrap.container import get_email_sender
from app.config.settings import get_settings
from app.identity.api.dependencies import require_platform_admin
from app.shared.application.ports import IEmailSender
from tests.fakes.fake_ports import FakeEmailSender
from tests.unit.beta_waitlist.test_beta_waitlist import MemoryStore, api  # noqa: F401


class BrokenSender(IEmailSender):
    async def send(self, *, to, subject, body, attachments=None, reply_to=None) -> None:  # type: ignore[no-untyped-def]
        raise RuntimeError("provider down")


async def _entry(store: MemoryStore, *, status: WaitlistStatus, **overrides: object) -> WaitlistEntry:
    entry = await store.upsert_interest(
        name=str(overrides.get("name", "Asha Rao")),
        work_email=str(overrides.get("work_email", "asha@example.com")),
        business_name=overrides.get("business_name", "Ledger & Co"),
        business_type=overrides.get("business_type", "Accounting firm"),
        bookkeeping_method=None,
        reporting_problem=None,
        weekly_feedback_ok=True,
    )
    result = await store.set_status(entry.id, status=status, notes=None)
    assert result is not None
    return result


@pytest.fixture
def sending(api):  # type: ignore[no-untyped-def]  # noqa: F811
    client, store, app = api
    sender = FakeEmailSender()
    app.dependency_overrides[get_email_sender] = lambda: sender
    app.dependency_overrides[require_platform_admin] = lambda: object()  # signed in as the platform admin
    return client, store, app, sender


def _send(client: TestClient, entry_id: uuid.UUID, **body: object):  # type: ignore[no-untyped-def]
    payload = {"subject": "Your place", "body": "Hi, sign up here.", **body}
    return client.post(f"/api/v1/admin/beta-waitlist/{entry_id}/send-invitation", json=payload)


# ------------------------------------------------------------------- the draft


async def test_the_draft_is_personal_and_links_to_sign_up(sending) -> None:  # type: ignore[no-untyped-def]
    client, store, _, sender = sending
    entry = await _entry(store, status=WaitlistStatus.INVITED)

    r = client.get(f"/api/v1/admin/beta-waitlist/{entry.id}/invitation-draft")

    assert r.status_code == 200
    draft = r.json()
    base = get_settings().frontend_base_url
    assert draft["to"] == "asha@example.com" and draft["is_firm"] is True
    assert draft["body"].startswith("Hi Asha,") and "Ledger & Co" in draft["body"]
    assert f"{base}/app/signup" in draft["body"] and "asha@example.com" in draft["body"]
    assert get_settings().support_email in draft["body"]
    assert sender.sent == []  # reading the draft sends nothing


async def test_a_firm_and_a_business_get_different_wording(sending) -> None:  # type: ignore[no-untyped-def]
    _, store, _, _ = sending
    firm = await _entry(store, status=WaitlistStatus.INVITED)
    shop = await _entry(
        store,
        status=WaitlistStatus.INVITED,
        name="Ben",
        work_email="ben@example.com",
        business_name="Ben's Bakery",
        business_type="Home bakery",
    )
    settings = get_settings()

    firm_draft = build_invitation_draft(
        firm, frontend_base_url=settings.frontend_base_url, support_email="s@x.co"
    )
    shop_draft = build_invitation_draft(
        shop, frontend_base_url=settings.frontend_base_url, support_email="s@x.co"
    )

    assert "accounting or bookkeeping firm" in firm_draft.body and firm_draft.is_firm
    assert "accounting or bookkeeping firm" not in shop_draft.body and not shop_draft.is_firm
    assert shop_draft.body.startswith("Hi Ben,")


# -------------------------------------------------------------------- sending


async def test_it_sends_exactly_what_the_owner_edited_and_records_it(sending) -> None:  # type: ignore[no-untyped-def]
    client, store, _, sender = sending
    entry = await _entry(store, status=WaitlistStatus.INVITED)

    r = _send(
        client, entry.id, subject="A note before you start", body="Hi Asha, my own words.\n\nSign up soon."
    )

    assert r.status_code == 200 and r.json()["invitation_sent_at"] is not None
    assert len(sender.sent) == 1
    sent = sender.sent[0]
    assert sent["to"] == "asha@example.com"
    assert (
        sent["subject"] == "A note before you start"
        and sent["body"] == "Hi Asha, my own words.\n\nSign up soon."
    )
    assert sent["reply_to"] == get_settings().support_email  # replies reach support, not a no-reply box
    assert store.rows[entry.id].invitation_sent_at is not None


@pytest.mark.parametrize(
    "status",
    [WaitlistStatus.INTERESTED, WaitlistStatus.QUALIFIED, WaitlistStatus.PAUSED, WaitlistStatus.ONBOARDED],
)
async def test_only_someone_at_invited_can_be_emailed(sending, status: WaitlistStatus) -> None:  # type: ignore[no-untyped-def]
    client, store, _, sender = sending
    entry = await _entry(store, status=status)

    r = _send(client, entry.id)

    assert r.status_code == 409 and r.json()["error_code"] == "waitlist_not_invited"
    assert sender.sent == []


async def test_a_second_send_needs_an_explicit_resend(sending) -> None:  # type: ignore[no-untyped-def]
    client, store, _, sender = sending
    entry = await _entry(store, status=WaitlistStatus.INVITED)
    assert _send(client, entry.id).status_code == 200

    again = _send(client, entry.id)
    deliberate = _send(client, entry.id, resend=True)

    assert again.status_code == 409 and again.json()["error_code"] == "invitation_already_sent"
    assert deliberate.status_code == 200
    assert len(sender.sent) == 2


async def test_a_failing_provider_sends_nothing_and_marks_nothing(sending) -> None:  # type: ignore[no-untyped-def]
    client, store, app, _ = sending
    app.dependency_overrides[get_email_sender] = lambda: BrokenSender()
    entry = await _entry(store, status=WaitlistStatus.INVITED)

    r = _send(client, entry.id)

    assert r.status_code == 502 and r.json()["error_code"] == "invitation_email_failed"
    assert store.rows[entry.id].invitation_sent_at is None  # so it can simply be tried again


async def test_nothing_goes_to_an_unknown_entry_and_empty_messages_are_refused(sending) -> None:  # type: ignore[no-untyped-def]
    client, store, _, sender = sending
    entry = await _entry(store, status=WaitlistStatus.INVITED)

    assert _send(client, uuid.uuid4()).status_code == 404
    assert _send(client, entry.id, subject="").status_code == 422
    assert _send(client, entry.id, body="").status_code == 422
    assert sender.sent == []


async def test_anyone_who_is_not_the_platform_admin_is_refused(sending) -> None:  # type: ignore[no-untyped-def]
    client, store, app, sender = sending
    entry = await _entry(store, status=WaitlistStatus.INVITED)
    del app.dependency_overrides[require_platform_admin]

    draft = client.get(f"/api/v1/admin/beta-waitlist/{entry.id}/invitation-draft")
    send = _send(client, entry.id)

    assert draft.status_code in (401, 403) and send.status_code in (401, 403)
    assert sender.sent == []
