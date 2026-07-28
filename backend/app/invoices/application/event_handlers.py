from app.workers.config import QUEUE_OCR


async def handle_invoice_submitted(payload: dict) -> None:
    """Reacts to InvoiceSubmitted (relayed from the outbox — see
    workers/tasks/outbox_relay_task.py) by enqueuing the document-processing
    /matching pipeline. Routed through the outbox rather than enqueued
    directly inside SubmitInvoiceUseCase so the enqueue survives a crash
    between commit and task dispatch — see workers/tasks/ocr_tasks.py for
    the task this triggers.

    Imports get_task_queue lazily: this module is imported by
    bootstrap/event_handlers.py, which container.py itself imports, so a
    top-level import here would be circular.
    """
    from app.bootstrap.container import get_task_queue

    task_queue = get_task_queue()
    task_queue.enqueue(
        "app.workers.tasks.ocr_tasks.process_invoice_document",
        kwargs={"invoice_id": payload["aggregate_id"]},
        queue=QUEUE_OCR,
    )
