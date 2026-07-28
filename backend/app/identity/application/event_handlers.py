from app.workers.config import QUEUE_NOTIFICATIONS


async def handle_user_registered(payload: dict) -> None:
    """Reacts to UserRegistered (relayed from the outbox) by enqueuing the
    verification email. Routed through the outbox rather than sent directly
    inside RegisterUserUseCase so the send survives a crash between commit
    and dispatch — same reasoning as InvoiceSubmitted -> OCR enqueue
    (invoices/application/event_handlers.py).

    Imports get_task_queue lazily: this module is imported by
    bootstrap/event_handlers.py, which container.py itself imports.
    """
    from app.bootstrap.container import get_task_queue

    task_queue = get_task_queue()
    task_queue.enqueue(
        "app.workers.tasks.notification_tasks.send_verification_email",
        kwargs={
            "user_id": payload["aggregate_id"],
            "email": payload["email"],
            "display_name": payload["display_name"],
            "verification_token": payload["verification_token"],
        },
        queue=QUEUE_NOTIFICATIONS,
    )


async def handle_password_reset_requested(payload: dict) -> None:
    from app.bootstrap.container import get_task_queue

    task_queue = get_task_queue()
    task_queue.enqueue(
        "app.workers.tasks.notification_tasks.send_password_reset_email",
        kwargs={
            "user_id": payload["aggregate_id"],
            "email": payload["email"],
            "reset_token": payload["reset_token"],
        },
        queue=QUEUE_NOTIFICATIONS,
    )
