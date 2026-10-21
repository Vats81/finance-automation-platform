import enum
import uuid

from pydantic import BaseModel

from app.data_import.application.dtos import ImportSummary
from app.data_import.application.jobs import ImportJob, ImportJobStatus


class ImportDataType(str, enum.Enum):
    """Path-param type — FastAPI 422s any value outside this set
    automatically. Only the flat, one-row-per-record entities are supported
    in this slice; Sales/Purchases (line items) and bank statements need a
    different import model and are deferred — see the Slice 7 plan.
    """

    CUSTOMERS = "customers"
    VENDORS = "vendors"
    PRODUCTS = "products"
    EXPENSES = "expenses"


class PreviewResponse(BaseModel):
    headers: list[str]
    sample_rows: list[dict[str, str]]
    canonical_fields: list[str]
    required_fields: list[str]
    row_count: int


class ImportRowErrorResponse(BaseModel):
    row_number: int
    message: str


class ImportSummaryResponse(BaseModel):
    total_rows: int
    created: int
    skipped_duplicates: int
    errors: list[ImportRowErrorResponse]

    @classmethod
    def from_domain(cls, summary: ImportSummary) -> "ImportSummaryResponse":
        return cls(
            total_rows=summary.total_rows,
            created=summary.created,
            skipped_duplicates=summary.skipped_duplicates,
            errors=[
                ImportRowErrorResponse(row_number=e.row_number, message=e.message) for e in summary.errors
            ],
        )


class ImportJobResponse(BaseModel):
    job_id: uuid.UUID
    status: ImportJobStatus
    processed_rows: int
    total_rows: int
    summary: ImportSummaryResponse | None = None
    error: str | None = None

    @classmethod
    def from_job(cls, job: ImportJob) -> "ImportJobResponse":
        return cls(
            job_id=job.id,
            status=job.status,
            processed_rows=job.processed_rows,
            total_rows=job.total_rows,
            summary=ImportSummaryResponse.from_domain(job.summary) if job.summary else None,
            error=job.error,
        )
