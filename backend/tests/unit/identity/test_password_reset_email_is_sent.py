"""The password-reset email is sent by the API itself, so it works with no background worker."""

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.rate_limit import limiter
from app.bootstrap.app_factory import create_app
from app.bootstrap.container import get_email_sender, get_uow
from app.config.settings import get_settings
from app.identity.domain.entities import User
from app.identity.domain.value_objects import EmailAddress
from app.shared.application.ports import IEmailSender
from tests.fakes.fake_ports import FakeEmailSender, FakePasswordHasher
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


class BrokenEmailSender(IEmailSender):
    async def send(self, *, to: str, subject: str, body: str, attachments=None) -> None:  # type: ignore[no-untyped-def]
        raise RuntimeError("mail provider is down")


@pytest.fixture
def world() -> Iterator[tuple[FakeUnitOfWork, FakeEmailSender, TestClient, User]]:
    limiter.enabled = False
    uow = FakeUnitOfWork()
    user = User.register(
        email=EmailAddress("owner@example.com"),
        display_name="Owner",
        password_hash=FakePasswordHasher().hash("old-password"),
        verification_token="t",
        verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    uow.users.add(user)
    sender = FakeEmailSender()
    app = create_app()
    app.dependency_overrides[get_uow] = lambda: uow
    app.dependency_overrides[get_email_sender] = lambda: sender
    yield uow, sender, TestClient(app, raise_server_exceptions=False), user
    limiter.enabled = True


def _request(client: TestClient, email: str):  # type: ignore[no-untyped-def]
    return client.post("/api/v1/auth/request-password-reset", json={"email": email})


def test_a_known_account_gets_one_email_with_a_working_link(
    world: tuple[FakeUnitOfWork, FakeEmailSender, TestClient, User],
) -> None:
    _, sender, client, user = world

    response = _request(client, "owner@example.com")

    assert response.status_code == 204
    assert len(sender.sent) == 1
    sent = sender.sent[0]
    assert sent["to"] == "owner@example.com" and sent["subject"] == "Reset your password"
    base = get_settings().frontend_base_url
    assert f"{base}/reset-password?uid={user.id}&token=" in sent["body"]
    assert user.password_reset_token_hash is not None  # a real token was issued


def test_an_unknown_address_gets_nothing_and_the_same_answer(
    world: tuple[FakeUnitOfWork, FakeEmailSender, TestClient, User],
) -> None:
    _, sender, client, _ = world

    response = _request(client, "nobody@example.com")

    assert response.status_code == 204 and sender.sent == []


def test_a_failing_mail_provider_never_changes_the_answer(
    world: tuple[FakeUnitOfWork, FakeEmailSender, TestClient, User],
) -> None:
    uow, _, client, _ = world
    client.app.dependency_overrides[get_email_sender] = lambda: BrokenEmailSender()  # type: ignore[attr-defined]

    response = _request(client, "owner@example.com")

    assert response.status_code == 204  # no 500, so it cannot be used to tell which accounts exist


def test_the_emailed_link_actually_resets_the_password(
    world: tuple[FakeUnitOfWork, FakeEmailSender, TestClient, User],
) -> None:
    _, sender, client, user = world
    _request(client, "owner@example.com")
    token = sender.sent[0]["body"].split("token=")[1].split()[0]

    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"user_id": str(user.id), "token": token, "new_password": "a-brand-new-password"},
    )

    assert reset.status_code == 200, reset.text
