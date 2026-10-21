import pytest

from app.bootstrap import container
from app.config.settings import get_settings
from app.shared.infrastructure.email_sender import ConsoleEmailSender
from app.shared.infrastructure.whatsapp_sender import ConsoleWhatsAppSender


@pytest.fixture
def isolated_env(monkeypatch: pytest.MonkeyPatch):
    # Real-looking provider settings that must be ignored in a restore drill.
    monkeypatch.setenv("RESEND_API_KEY", "re_live_key")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "twilio")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_x")
    monkeypatch.setenv("DISABLE_EXTERNAL_SIDE_EFFECTS", "true")
    for fn in (
        get_settings,
        container.get_email_sender,
        container.get_whatsapp_sender,
        container.get_payment_gateway,
    ):
        fn.cache_clear()
    yield
    monkeypatch.undo()
    for fn in (
        get_settings,
        container.get_email_sender,
        container.get_whatsapp_sender,
        container.get_payment_gateway,
    ):
        fn.cache_clear()


def test_a_drill_environment_cannot_email_message_or_charge_anyone(
    isolated_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert isinstance(container.get_email_sender(), ConsoleEmailSender)
    assert isinstance(container.get_whatsapp_sender(), ConsoleWhatsAppSender)

    seen: dict[str, str] = {}

    class RecordingGateway:
        def __init__(self, *, secret_key: str, webhook_secret: str) -> None:
            seen.update(secret_key=secret_key, webhook_secret=webhook_secret)

    monkeypatch.setattr(container, "StripeGateway", RecordingGateway)
    container.get_payment_gateway.cache_clear()
    container.get_payment_gateway()
    assert seen == {"secret_key": "", "webhook_secret": ""}
