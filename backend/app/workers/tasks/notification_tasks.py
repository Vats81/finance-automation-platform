import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.approvals.domain.value_objects import ApprovalStepStatus, ApprovalWorkflowStatus
from app.approvals.infrastructure.models import ApprovalWorkflowModel
from app.bootstrap.container import get_container
from app.config.settings import get_settings
from app.workers.celery_app import celery_app
from app.workers.config import QUEUE_NOTIFICATIONS

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.workers.tasks.notification_tasks.send_verification_email",
    queue=QUEUE_NOTIFICATIONS,
)
def send_verification_email(user_id: str, email: str, display_name: str, verification_token: str) -> None:
    """Triggered by UserRegistered (identity/application/event_handlers.py)
    for the SMB Finance Manager product's self-serve signup. Uses
    IEmailSender (ConsoleEmailSender in local dev, SmtpEmailSender once
    SMTP_* settings are configured) rather than a hard dependency on a
    specific email provider.
    """
    asyncio.run(_send_verification_email_async(user_id, email, display_name, verification_token))


async def _send_verification_email_async(
    user_id: str, email: str, display_name: str, verification_token: str
) -> None:
    from app.bootstrap.container import get_email_sender

    settings = get_settings()
    link = f"{settings.frontend_base_url}/verify-email?uid={user_id}&token={verification_token}"
    await get_email_sender().send(
        to=email,
        subject="Verify your email",
        body=(
            f"Hi {display_name},\n\n"
            f"Welcome! Please verify your email address to activate your account:\n\n{link}\n\n"
            f"This link expires in {settings.email_verification_ttl_hours} hours."
        ),
    )


@celery_app.task(
    name="app.workers.tasks.notification_tasks.send_password_reset_email",
    queue=QUEUE_NOTIFICATIONS,
)
def send_password_reset_email(user_id: str, email: str, reset_token: str) -> None:
    asyncio.run(_send_password_reset_email_async(user_id, email, reset_token))


async def _send_password_reset_email_async(user_id: str, email: str, reset_token: str) -> None:
    from app.bootstrap.container import get_email_sender

    settings = get_settings()
    link = f"{settings.frontend_base_url}/reset-password?uid={user_id}&token={reset_token}"
    await get_email_sender().send(
        to=email,
        subject="Reset your password",
        body=(
            f"We received a request to reset your password. Use the link below to choose a new one:\n\n"
            f"{link}\n\nThis link expires in {settings.password_reset_ttl_hours} hours. "
            f"If you didn't request this, you can safely ignore this email."
        ),
    )


@celery_app.task(
    name="app.workers.tasks.notification_tasks.sweep_approval_reminders",
    queue=QUEUE_NOTIFICATIONS,
)
def sweep_approval_reminders() -> int:
    """Periodic sweep (workers/beat_schedule.py) that logs a reminder for
    every in-progress workflow's current pending step. Stands in for a real
    email/Slack notification provider (Phase 2) — reads ORM models directly
    rather than going through the domain/repository layer since this is a
    pure read-only reporting task, not a command that mutates state.
    """
    return asyncio.run(_sweep_approval_reminders_async())


async def _sweep_approval_reminders_async() -> int:
    container = get_container()
    reminders_sent = 0

    async with container.session_factory() as session:
        stmt = (
            select(ApprovalWorkflowModel)
            .options(selectinload(ApprovalWorkflowModel.steps))
            .where(ApprovalWorkflowModel.status == ApprovalWorkflowStatus.IN_PROGRESS.value)
        )
        result = await session.execute(stmt)
        workflows = result.unique().scalars().all()

        for workflow_model in workflows:
            current = next(
                (s for s in sorted(workflow_model.steps, key=lambda s: s.step_number)
                 if s.status == ApprovalStepStatus.PENDING.value),
                None,
            )
            if current is not None:
                logger.info(
                    "Approval reminder: invoice %s awaiting %s approval (step %s)",
                    workflow_model.invoice_id,
                    current.required_role,
                    current.step_number,
                )
                reminders_sent += 1

    return reminders_sent
