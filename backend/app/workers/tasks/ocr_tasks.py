import asyncio
import uuid

from app.bootstrap.container import get_container
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.invoices.application.commands.record_ocr_result import RecordOcrResultCommand, RecordOcrResultUseCase
from app.invoices.infrastructure.document_processing_client import SimulatedDocumentProcessingClient
from app.workers.celery_app import celery_app
from app.workers.config import DEFAULT_MAX_RETRIES, DEFAULT_RETRY_BACKOFF_SECONDS, QUEUE_OCR


@celery_app.task(
    name="app.workers.tasks.ocr_tasks.process_invoice_document",
    queue=QUEUE_OCR,
    bind=True,
    max_retries=DEFAULT_MAX_RETRIES,
    default_retry_delay=DEFAULT_RETRY_BACKOFF_SECONDS,
)
def process_invoice_document(self, invoice_id: str) -> str:
    try:
        return asyncio.run(_process_invoice_document_async(invoice_id))
    except Exception as exc:  # noqa: BLE001 - hand off to Celery's retry policy
        raise self.retry(exc=exc) from exc


async def _process_invoice_document_async(invoice_id: str) -> str:
    container = get_container()
    document_processing_client = SimulatedDocumentProcessingClient()

    async with container.session_factory() as session:
        uow = AppUnitOfWork(session)
        use_case = RecordOcrResultUseCase(uow, document_processing_client)
        invoice = await use_case.execute(RecordOcrResultCommand(invoice_id=uuid.UUID(invoice_id)))
        return invoice.status.value
