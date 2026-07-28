from app.config.settings import Settings
from app.integrations.application.queries.get_integration_status import GetIntegrationStatusUseCase


async def test_all_defaults_are_not_connected() -> None:
    status = GetIntegrationStatusUseCase(Settings()).execute()

    assert status.email.connected is False
    assert status.whatsapp.connected is False
    assert status.ai_assistant.connected is False
    assert status.document_storage.connected is False


async def test_smtp_host_set_marks_email_connected() -> None:
    # Settings' fields are alias-only (no populate_by_name), so overrides
    # must use the env-var alias names, e.g. SMTP_HOST not smtp_host.
    status = GetIntegrationStatusUseCase(Settings(SMTP_HOST="smtp.example.com")).execute()

    assert status.email.connected is True
    assert "smtp.example.com" in status.email.detail


async def test_twilio_provider_marks_whatsapp_connected() -> None:
    status = GetIntegrationStatusUseCase(Settings(WHATSAPP_PROVIDER="twilio")).execute()

    assert status.whatsapp.connected is True


async def test_anthropic_provider_marks_ai_assistant_connected_and_mentions_model() -> None:
    status = GetIntegrationStatusUseCase(
        Settings(AI_PROVIDER="anthropic", ANTHROPIC_MODEL="claude-sonnet-5")
    ).execute()

    assert status.ai_assistant.connected is True
    assert "claude-sonnet-5" in status.ai_assistant.detail


async def test_azure_storage_connection_string_marks_document_storage_connected() -> None:
    status = GetIntegrationStatusUseCase(
        Settings(AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;...")
    ).execute()

    assert status.document_storage.connected is True
