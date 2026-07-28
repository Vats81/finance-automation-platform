import enum

from pydantic import BaseModel

from app.data_import.application.dtos import ImportSummary


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
