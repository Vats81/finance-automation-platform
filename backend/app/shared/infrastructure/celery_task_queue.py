import logging

from celery import Celery
from kombu.exceptions import KombuError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.shared.application.exceptions import TaskQueueUnavailableException
from app.shared.application.ports import ITaskQueue

logger = logging.getLogger(__name__)

_retry_transient = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type(KombuError),
)


class CeleryTaskQueueAdapter(ITaskQueue):
    """Adapts the Celery app (RabbitMQ broker) to the ITaskQueue port.

    Uses `send_task` by registered name rather than importing task functions
    directly, so the API process never needs to import Celery task modules
    (which would pull in worker-only dependencies).
    """

    def __init__(self, celery_app: Celery) -> None:
        self._celery_app = celery_app

    @_retry_transient
    def enqueue(self, task_name: str, *, kwargs: dict, queue: str = "default") -> str:
        try:
            result = self._celery_app.send_task(task_name, kwargs=kwargs, queue=queue)
            return result.id
        except KombuError as exc:
            logger.error("Failed to enqueue task %s: %s", task_name, exc)
            raise TaskQueueUnavailableException(f"Failed to enqueue {task_name}") from exc
