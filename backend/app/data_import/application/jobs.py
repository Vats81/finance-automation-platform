import asyncio
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum

from app.data_import.application.dtos import ImportSummary, ProgressCallback

logger = logging.getLogger(__name__)

_KEEP_FINISHED_SECONDS = 60 * 60
_MAX_JOBS = 200


class ImportJobStatus(str, Enum):
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class ImportJob:
    id: uuid.UUID
    business_id: uuid.UUID
    total_rows: int
    status: ImportJobStatus = ImportJobStatus.RUNNING
    processed_rows: int = 0
    summary: ImportSummary | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.monotonic)
    finished_at: float | None = None


ImportRunner = Callable[[ProgressCallback], Awaitable[ImportSummary]]


class ImportJobRegistry:
    """In-memory registry of background CSV imports, so a big file can report
    progress instead of holding one request open for a minute or more.

    Deliberately in-process (no Celery worker is deployed, see DEPLOY.md): the
    state lives in this API process, so a restart mid-import loses the job.
    That is safe to recover from because every importer is idempotent — a
    re-upload skips what was already created — and the API reports an unknown
    job as such so the UI can say so.
    """

    def __init__(self) -> None:
        self._jobs: dict[uuid.UUID, ImportJob] = {}
        # Strong references: the event loop only holds weak ones to tasks.
        self._tasks: set[asyncio.Task[None]] = set()

    def get(self, job_id: uuid.UUID) -> ImportJob | None:
        return self._jobs.get(job_id)

    def running_for_business(self, business_id: uuid.UUID) -> ImportJob | None:
        return next(
            (
                j
                for j in self._jobs.values()
                if j.business_id == business_id and j.status == ImportJobStatus.RUNNING
            ),
            None,
        )

    def start(self, *, business_id: uuid.UUID, total_rows: int, runner: ImportRunner) -> ImportJob:
        self._prune()
        job = ImportJob(id=uuid.uuid4(), business_id=business_id, total_rows=total_rows)
        self._jobs[job.id] = job
        task = asyncio.create_task(self._run(job, runner))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return job

    async def _run(self, job: ImportJob, runner: ImportRunner) -> None:
        def on_progress(processed: int, _total: int) -> None:
            job.processed_rows = processed

        try:
            job.summary = await runner(on_progress)
            job.processed_rows = job.total_rows
            job.status = ImportJobStatus.DONE
        except Exception:  # noqa: BLE001 - reported on the job, never raised into the loop
            logger.exception("Import job %s failed", job.id)
            job.error = (
                "The import stopped unexpectedly. Rows already imported are kept; upload again to continue."
            )
            job.status = ImportJobStatus.FAILED
        finally:
            job.finished_at = time.monotonic()

    def _prune(self) -> None:
        now = time.monotonic()
        for job_id, job in list(self._jobs.items()):
            if job.finished_at is not None and now - job.finished_at > _KEEP_FINISHED_SECONDS:
                del self._jobs[job_id]
        # Hard cap as a backstop; drop the oldest finished jobs first.
        if len(self._jobs) >= _MAX_JOBS:
            finished = sorted(
                (j for j in self._jobs.values() if j.finished_at is not None),
                key=lambda j: j.finished_at or 0,
            )
            for job in finished[: len(self._jobs) - _MAX_JOBS + 1]:
                del self._jobs[job.id]


_registry = ImportJobRegistry()


def get_import_job_registry() -> ImportJobRegistry:
    return _registry
