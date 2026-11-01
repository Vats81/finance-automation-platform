"""The account emails (verify your address, reset your password): one place for their wording.

Used by the background tasks (workers/tasks/notification_tasks.py) and by the API process itself
when it sends them directly (SEND_AUTH_EMAILS_INLINE), so the two can never drift apart.
"""

import logging
import uuid

from app.config.settings import Settings
from app.shared.application.ports import IEmailSender

logger = logging.getLogger(__name__)


async def send_verification_email(
    sender: IEmailSender,
    settings: Settings,
    *,
    user_id: str | uuid.UUID,
    email: str,
    display_name: str,
    verification_token: str,
) -> None:
    link = f"{settings.frontend_base_url}/verify-email?uid={user_id}&token={verification_token}"
    await sender.send(
        to=email,
        subject="Verify your email",
        body=(
            f"Hi {display_name},\n\n"
            f"Welcome! Please verify your email address to activate your account:\n\n{link}\n\n"
            f"This link expires in {settings.email_verification_ttl_hours} hours."
        ),
    )


async def send_password_reset_email(
    sender: IEmailSender,
    settings: Settings,
    *,
    user_id: str | uuid.UUID,
    email: str,
    reset_token: str,
) -> None:
    link = f"{settings.frontend_base_url}/reset-password?uid={user_id}&token={reset_token}"
    await sender.send(
        to=email,
        subject="Reset your password",
        body=(
            f"We received a request to reset your password. Use the link below to choose a new one:\n\n"
            f"{link}\n\nThis link expires in {settings.password_reset_ttl_hours} hours. "
            f"If you didn't request this, you can safely ignore this email."
        ),
    )
