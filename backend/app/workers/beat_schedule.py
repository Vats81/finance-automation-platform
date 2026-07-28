"""Celery Beat periodic schedule.

Entries are added incrementally as the tasks they reference are built —
referencing a task name Beat can enqueue but no worker has registered yet
would enqueue messages the worker then fails on "unregistered task" every
time Beat fires, so each entry lands in the same commit as its task.
"""

from app.config.settings import get_settings

settings = get_settings()

BEAT_SCHEDULE: dict = {
    "relay-outbox-messages": {
        "task": "app.workers.tasks.outbox_relay_task.relay_outbox_messages",
        "schedule": settings.outbox_relay_poll_seconds,
    },
    "sweep-approval-reminders": {
        "task": "app.workers.tasks.notification_tasks.sweep_approval_reminders",
        "schedule": 300.0,  # every 5 minutes
    },
}
