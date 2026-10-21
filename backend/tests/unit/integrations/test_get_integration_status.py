from app.config.settings import Settings
from app.integrations.application.queries.get_integration_status import GetIntegrationStatusUseCase


async def test_all_defaults_are_not_connected() -> None:
    status = GetIntegrationStatusUseCase(Settings()).execute()

    assert status.email.connected is False
    assert status.whatsapp.connected is False
    assert status.ai_assistant.connected is False
    assert status.document_storage.connected is False
    assert status.billing.connected is False


async def test_smtp_host_set_marks_email_connected() -> None:
    # Settings' fields are alias-only (no populate_by_name), so overrides
    # must use the env-var alias names, e.g. SMTP_HOST not smtp_host.
    status = GetIntegrationStatusUseCase(Settings(SMTP_HOST="smtp.example.com")).execute()

    assert status.email.connected is True
    assert "smtp.example.com" in status.email.detail


async def test_resend_api_key_marks_email_connected_and_takes_priority_over_smtp() -> None:
    status = GetIntegrationStatusUseCase(
        Settings(RESEND_API_KEY="re_test_key", SMTP_HOST="smtp.example.com")
    ).execute()

    assert status.email.connected is True
    assert "Resend" in status.email.detail


async def test_twilio_provider_marks_whatsapp_connected() -> None:
    status = GetIntegrationStatusUseCase(Settings(WHATSAPP_PROVIDER="twilio")).execute()

    assert status.whatsapp.connected is True


async def test_anthropic_provider_marks_ai_assistant_connected_and_mentions_model() -> None:
    status = GetIntegrationStatusUseCase(
        Settings(AI_PROVIDER="anthropic", ANTHROPIC_MODEL="claude-sonnet-5")
    ).execute()

    assert status.ai_assistant.connected is True
    assert "claude-sonnet-5" in status.ai_assistant.detail


async def test_groq_provider_marks_ai_assistant_connected_and_mentions_both_models() -> None:
    status = GetIntegrationStatusUseCase(
        Settings(
            AI_PROVIDER="groq",
            GROQ_MODEL="llama-3.3-70b-versatile",
            GROQ_VISION_MODEL="llama-4-scout",
        )
    ).execute()

    assert status.ai_assistant.connected is True
    assert "llama-3.3-70b-versatile" in status.ai_assistant.detail
    assert "llama-4-scout" in status.ai_assistant.detail


async def test_default_ai_assistant_detail_mentions_the_free_groq_option() -> None:
    status = GetIntegrationStatusUseCase(Settings()).execute()

    assert status.ai_assistant.connected is False
    assert "GROQ_API_KEY" in status.ai_assistant.detail


async def test_azure_storage_connection_string_marks_document_storage_connected() -> None:
    status = GetIntegrationStatusUseCase(
        Settings(AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;...")
    ).execute()

    assert status.document_storage.connected is True


async def test_stripe_secret_key_marks_billing_connected() -> None:
    status = GetIntegrationStatusUseCase(Settings(STRIPE_SECRET_KEY="sk_test_dummy")).execute()

    assert status.billing.connected is True


async def test_resend_test_sender_is_reported_as_limited_not_plain_connected() -> None:
    # Resend's shared test sender only delivers to the account owner, so
    # "Connected" would overstate what works for anyone else.
    status = GetIntegrationStatusUseCase(
        Settings(RESEND_API_KEY="re_test_key", SMTP_FROM_ADDRESS="onboarding@resend.dev")
    ).execute()

    assert status.email.connected is True
    assert status.email.limited is True
    assert "test mode" in status.email.detail


async def test_resend_with_a_real_sender_domain_is_fully_connected() -> None:
    status = GetIntegrationStatusUseCase(
        Settings(RESEND_API_KEY="re_live_key", SMTP_FROM_ADDRESS="hello@acme.com")
    ).execute()

    assert status.email.connected is True
    assert status.email.limited is False


async def test_twilio_sandbox_number_is_reported_as_limited() -> None:
    for sandbox_number in ("+14155238886", "14155238886", "+1 (415) 523-8886"):
        status = GetIntegrationStatusUseCase(
            Settings(WHATSAPP_PROVIDER="twilio", TWILIO_WHATSAPP_FROM=sandbox_number)
        ).execute()

        assert status.whatsapp.connected is True, sandbox_number
        assert status.whatsapp.limited is True, sandbox_number
        assert "Sandbox" in status.whatsapp.detail


async def test_twilio_with_any_other_number_is_still_limited() -> None:
    # Regression test from a QA report: only the sandbox number used to be
    # flagged, so a different configured sender showed a plain "Connected" /
    # "Sending real WhatsApp messages". The limit isn't about the number —
    # this app has no template support, so with ANY sender WhatsApp only
    # delivers to people who messaged within the last 24 hours.
    for number in ("+919876543210", "+447700900123", "whatsapp:+12025550123"):
        status = GetIntegrationStatusUseCase(
            Settings(WHATSAPP_PROVIDER="twilio", TWILIO_WHATSAPP_FROM=number)
        ).execute()

        assert status.whatsapp.connected is True, number
        assert status.whatsapp.limited is True, number
        assert "24" in status.whatsapp.detail
        assert "real WhatsApp messages" not in status.whatsapp.detail

