from dataclasses import dataclass

from app.config.settings import Settings


@dataclass(frozen=True)
class ProviderStatus:
    connected: bool
    detail: str


@dataclass(frozen=True)
class IntegrationsStatus:
    email: ProviderStatus
    whatsapp: ProviderStatus
    ai_assistant: ProviderStatus
    document_storage: ProviderStatus
    billing: ProviderStatus


class GetIntegrationStatusUseCase:
    """Reports whether each pluggable provider is actually configured, by
    mirroring the exact same conditional logic bootstrap/container.py
    already uses to choose between a Console fallback and a real adapter —
    so this status can never drift from what's actually wired at runtime.

    Takes `Settings` directly (not `get_settings()` internally) so tests
    can construct overrides without depending on process env/.env state.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def execute(self) -> IntegrationsStatus:
        return IntegrationsStatus(
            email=self._email_status(),
            whatsapp=self._whatsapp_status(),
            ai_assistant=self._ai_assistant_status(),
            document_storage=self._document_storage_status(),
            billing=self._billing_status(),
        )

    def _email_status(self) -> ProviderStatus:
        if self._settings.smtp_configured:
            return ProviderStatus(
                connected=True, detail=f"Sending real email via {self._settings.smtp_host}."
            )
        return ProviderStatus(
            connected=False,
            detail="Not configured — set SMTP_HOST, SMTP_USERNAME, and SMTP_PASSWORD to send real "
            "email. Currently logging to the console instead.",
        )

    def _whatsapp_status(self) -> ProviderStatus:
        if self._settings.whatsapp_provider == "twilio":
            return ProviderStatus(connected=True, detail="Sending real WhatsApp messages via Twilio.")
        return ProviderStatus(
            connected=False,
            detail="Not configured — set WHATSAPP_PROVIDER=twilio along with TWILIO_ACCOUNT_SID, "
            "TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM to send real WhatsApp messages. Currently "
            "logging to the console instead.",
        )

    def _ai_assistant_status(self) -> ProviderStatus:
        if self._settings.ai_provider == "anthropic":
            return ProviderStatus(
                connected=True,
                detail=f"Using Anthropic Claude ({self._settings.anthropic_model}) for the AI "
                "Assistant, Insights, Forecasting, and Receipt Scanner.",
            )
        return ProviderStatus(
            connected=False,
            detail="Not configured — set AI_PROVIDER=anthropic and ANTHROPIC_API_KEY to enable real "
            "AI answers. Currently using a placeholder response instead.",
        )

    def _document_storage_status(self) -> ProviderStatus:
        if self._settings.azure_storage_connection_string:
            return ProviderStatus(connected=True, detail="Azure Blob Storage is configured.")
        return ProviderStatus(
            connected=False,
            detail="Not configured — set AZURE_STORAGE_CONNECTION_STRING to enable document uploads.",
        )

    def _billing_status(self) -> ProviderStatus:
        if self._settings.stripe_configured:
            return ProviderStatus(connected=True, detail="Real subscription billing is live via Stripe.")
        return ProviderStatus(
            connected=False,
            detail="Not configured — set STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, "
            "STRIPE_PRICE_ID_STARTER, and STRIPE_PRICE_ID_PRO to enable real billing. Plan changes are "
            "currently a free, unpaid field flip.",
        )
