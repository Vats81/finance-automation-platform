from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration, sourced from environment variables (.env)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    app_env: str = Field(default="local", alias="APP_ENV")
    app_name: str = Field(default="finance-automation-platform", alias="APP_NAME")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_allowed_origins: str = Field(default="http://localhost:3000", alias="CORS_ALLOWED_ORIGINS")

    # --- Database ---
    database_url: str = Field(
        default="postgresql+asyncpg://fap_user:fap_dev_password@localhost:5432/fap_db",
        alias="DATABASE_URL",
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg2://fap_user:fap_dev_password@localhost:5432/fap_db",
        alias="DATABASE_URL_SYNC",
    )

    # --- Redis ---
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/1", alias="CELERY_RESULT_BACKEND")

    # --- RabbitMQ / Celery ---
    celery_broker_url: str = Field(
        default="amqp://fap_user:fap_dev_password@localhost:5672//", alias="CELERY_BROKER_URL"
    )

    # --- Azure Blob Storage ---
    azure_storage_connection_string: str = Field(default="", alias="AZURE_STORAGE_CONNECTION_STRING")
    azure_storage_container_name: str = Field(default="documents", alias="AZURE_STORAGE_CONTAINER_NAME")

    # --- Entra ID ---
    entra_tenant_id: str = Field(default="", alias="ENTRA_TENANT_ID")
    entra_api_client_id: str = Field(default="", alias="ENTRA_API_CLIENT_ID")
    entra_api_application_id_uri: str = Field(default="", alias="ENTRA_API_APPLICATION_ID_URI")
    entra_jwks_uri: str = Field(default="", alias="ENTRA_JWKS_URI")
    entra_issuer: str = Field(default="", alias="ENTRA_ISSUER")
    auth_dev_mode: bool = Field(default=True, alias="AUTH_DEV_MODE")
    auth_dev_mode_shared_secret: str = Field(
        default="dev-only-insecure-secret", alias="AUTH_DEV_MODE_SHARED_SECRET"
    )

    # --- Approval thresholds (integer cents, USD) ---
    approval_threshold_l1_max: int = Field(default=100_000, alias="APPROVAL_THRESHOLD_L1_MAX")
    approval_threshold_l2_max: int = Field(default=1_000_000, alias="APPROVAL_THRESHOLD_L2_MAX")

    # --- Rate limiting ---
    rate_limit_default: str = Field(default="100/minute", alias="RATE_LIMIT_DEFAULT")
    rate_limit_write: str = Field(default="30/minute", alias="RATE_LIMIT_WRITE")

    # --- OpenTelemetry ---
    otel_service_name: str = Field(default="fap-backend", alias="OTEL_SERVICE_NAME")
    otel_exporter: str = Field(default="console", alias="OTEL_EXPORTER")

    # --- Outbox relay ---
    outbox_relay_poll_seconds: float = Field(default=3.0, alias="OUTBOX_RELAY_POLL_SECONDS")
    outbox_relay_batch_size: int = Field(default=50, alias="OUTBOX_RELAY_BATCH_SIZE")

    # --- Self-serve (local) auth: SMB Finance Manager product ---
    jwt_secret_key: str = Field(default="dev-only-insecure-jwt-secret", alias="JWT_SECRET_KEY")
    jwt_access_token_ttl_days: int = Field(default=7, alias="JWT_ACCESS_TOKEN_TTL_DAYS")
    email_verification_ttl_hours: int = Field(default=24, alias="EMAIL_VERIFICATION_TTL_HOURS")
    password_reset_ttl_hours: int = Field(default=2, alias="PASSWORD_RESET_TTL_HOURS")
    frontend_base_url: str = Field(default="http://localhost:3000", alias="FRONTEND_BASE_URL")

    # --- Outbound email (verification / password reset links) ---
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str = Field(default="", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from_address: str = Field(default="noreply@example.com", alias="SMTP_FROM_ADDRESS")

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host)

    # --- Resend API (HTTPS-based email — see shared/infrastructure/email_sender.py
    # for why this exists alongside SMTP: outbound SMTP ports are silently
    # blocked on several free-tier hosts, including this app's own Render
    # deployment; preferred over SMTP whenever set). ---
    resend_api_key: str = Field(default="", alias="RESEND_API_KEY")

    @property
    def email_configured(self) -> bool:
        return bool(self.resend_api_key) or self.smtp_configured

    # --- Outbound WhatsApp (report delivery) ---
    # Explicit provider flag rather than an inferred "is a SID set" toggle
    # like smtp_configured — a Twilio SID being present is a less natural
    # on/off signal than an SMTP host being present.
    whatsapp_provider: Literal["console", "twilio"] = Field(default="console", alias="WHATSAPP_PROVIDER")
    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", alias="TWILIO_AUTH_TOKEN")
    twilio_whatsapp_from: str = Field(default="", alias="TWILIO_WHATSAPP_FROM")

    # --- AI Business Assistant ---
    ai_provider: Literal["console", "anthropic"] = Field(default="console", alias="AI_PROVIDER")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    # Verify the exact current model id in Anthropic's docs when wiring a
    # real key — this default is just a reasonable starting point.
    anthropic_model: str = Field(default="claude-sonnet-5", alias="ANTHROPIC_MODEL")

    # --- One-time demo-account seeding (free-tier hosts with no shell access) ---
    # Blank by default, which disables the endpoint entirely (see api/seed.py).
    seed_secret: str = Field(default="", alias="SEED_SECRET")

    # --- Stripe billing ---
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")
    stripe_price_id_starter: str = Field(default="", alias="STRIPE_PRICE_ID_STARTER")
    stripe_price_id_pro: str = Field(default="", alias="STRIPE_PRICE_ID_PRO")

    @property
    def stripe_configured(self) -> bool:
        return bool(self.stripe_secret_key)

    @model_validator(mode="after")
    def _dev_auth_only_in_local(self) -> "Settings":
        if self.auth_dev_mode and self.app_env != "local":
            raise ValueError("AUTH_DEV_MODE must not be enabled outside APP_ENV=local")
        return self

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Settings are cached for process lifetime; overridden in tests via dependency override."""
    return Settings()
