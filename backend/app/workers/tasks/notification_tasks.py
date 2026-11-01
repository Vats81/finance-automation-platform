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
    from app.identity.application.auth_emails import send_verification_email as send

    await send(
        get_email_sender(),
        get_settings(),
        user_id=user_id,
        email=email,
        display_name=display_name,
        verification_token=verification_token,
    )


@celery_app.task(
    name="app.workers.tasks.notification_tasks.send_password_reset_email",
    queue=QUEUE_NOTIFICATIONS,
)
def send_password_reset_email(user_id: str, email: str, reset_token: str) -> None:
    asyncio.run(_send_password_reset_email_async(user_id, email, reset_token))


async def _send_password_reset_email_async(user_id: str, email: str, reset_token: str) -> None:
    from app.bootstrap.container import get_email_sender
    from app.identity.application.auth_emails import send_password_reset_email as send

    await send(get_email_sender(), get_settings(), user_id=user_id, email=email, reset_token=reset_token)


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
                (
                    s
                    for s in sorted(workflow_model.steps, key=lambda s: s.step_number)
                    if s.status == ApprovalStepStatus.PENDING.value
                ),
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
