from app.shared.domain.exceptions import DomainException


class ApplicationException(DomainException):
    """Base for application-layer errors (infrastructure reachable but degraded)."""

    error_code = "application_error"
    http_status = 502


class FileStorageUnavailableException(ApplicationException):
    error_code = "file_storage_unavailable"
    http_status = 503


class TaskQueueUnavailableException(ApplicationException):
    error_code = "task_queue_unavailable"
    http_status = 503
