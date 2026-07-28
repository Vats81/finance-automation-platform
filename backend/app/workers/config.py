"""Celery queue and retry defaults, shared by every task module.

Queues: `default` for general-purpose work, `ocr` for document-processing
tasks (invoices/domain — see invoices/infrastructure/document_processing_client.py
usage in workers/tasks/ocr_tasks.py), `notifications` for approval reminders
and similar user-facing sends. Keeping these separate lets us scale worker
concurrency per queue independently (e.g. more OCR workers than
notification workers) without touching task code.
"""

QUEUE_DEFAULT = "default"
QUEUE_OCR = "ocr"
QUEUE_NOTIFICATIONS = "notifications"

DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 5
