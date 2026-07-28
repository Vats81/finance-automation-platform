from celery import Celery
from celery.signals import worker_process_init
from kombu import Queue

from app.config.settings import get_settings
from app.shared.infrastructure.logging import configure_logging
from app.workers.beat_schedule import BEAT_SCHEDULE
from app.workers.config import QUEUE_DEFAULT, QUEUE_NOTIFICATIONS, QUEUE_OCR

settings = get_settings()

celery_app = Celery(
    "finance_automation_platform",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks.outbox_relay_task",
        "app.workers.tasks.ocr_tasks",
        "app.workers.tasks.notification_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_default_queue=QUEUE_DEFAULT,
    task_queues=(
        Queue(QUEUE_DEFAULT),
        Queue(QUEUE_OCR),
        Queue(QUEUE_NOTIFICATIONS),
    ),
    beat_schedule=BEAT_SCHEDULE,
)


@worker_process_init.connect
def _init_worker_logging(**kwargs) -> None:
    """Same structured-logging setup as the API process (app_factory.py) so
    worker and API logs are consistent JSON. Hooked to worker_process_init
    rather than run at module import time, since that fires once per
    actual worker process (including under prefork), not in Beat or the
    parent process that merely imports this module.
    """
    configure_logging(get_settings().log_level)
