import csv
import io
import json
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response

from app.api.rate_limit import limiter
from app.bootstrap.container import get_container, get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.api.dependencies import require_business_role
from app.business.api.permissions import CAN_WRITE
from app.config.settings import get_settings
from app.data_import.api.schemas import (
    ImportDataType,
    ImportJobResponse,
    ImportSummaryResponse,
    PreviewResponse,
)
from app.data_import.application import import_customers, import_expenses, import_products, import_vendors
from app.data_import.application.dtos import ImportSummary, ProgressCallback
from app.data_import.application.jobs import ImportJobRegistry, get_import_job_registry
from app.identity.domain.entities import User
from app.shared.domain.exceptions import ValidationException
from app.shared.infrastructure.csv_parser import MAX_UPLOAD_BYTES, parse_csv

router = APIRouter(prefix="/businesses/{business_id}/imports", tags=["data-import"])

settings = get_settings()

_can_write = CAN_WRITE



def _parse_column_mapping(raw: str) -> dict[str, str]:
    """The mapping arrives as a JSON string in a form field, so it is
    untrusted: anything other than an object of field -> header was a 500.
    """
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        raise ValidationException("column_mapping must be valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise ValidationException('column_mapping must be a JSON object, e.g. {"name": "Customer"}.')
    mapping: dict[str, str] = {}
    for field, header in parsed.items():
        if header is None or header == "":
            continue
        if not isinstance(header, str):
            raise ValidationException(f"column_mapping[{field!r}] must be a column name (text) or null.")
        mapping[str(field)] = header
    return mapping


async def _read_upload(file: UploadFile) -> bytes:
    # Read one byte past the cap so an oversized file is rejected without
    # buffering all of it in memory.
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    return content


async def _execute_import(
    uow: AppUnitOfWork,
    data_type: ImportDataType,
    business_id: uuid.UUID,
    rows: list[dict[str, str]],
    mapping: dict[str, str],
    on_progress: ProgressCallback | None = None,
) -> ImportSummary:
    if data_type == ImportDataType.CUSTOMERS:
        return await import_customers.ImportCustomersUseCase(uow).execute(
            business_id=business_id, rows=rows, column_mapping=mapping, on_progress=on_progress
        )
    if data_type == ImportDataType.VENDORS:
        return await import_vendors.ImportVendorsUseCase(uow).execute(
            business_id=business_id, rows=rows, column_mapping=mapping, on_progress=on_progress
        )
    if data_type == ImportDataType.PRODUCTS:
        return await import_products.ImportProductsUseCase(uow).execute(
            business_id=business_id, rows=rows, column_mapping=mapping, on_progress=on_progress
        )
    return await import_expenses.ImportExpensesUseCase(uow).execute(
        business_id=business_id, rows=rows, column_mapping=mapping, on_progress=on_progress
    )


_IMPORTER_MODULES = {
    ImportDataType.CUSTOMERS: import_customers,
    ImportDataType.VENDORS: import_vendors,
    ImportDataType.PRODUCTS: import_products,
    ImportDataType.EXPENSES: import_expenses,
}


@router.post("/{data_type}/preview", response_model=PreviewResponse)
@limiter.limit(settings.rate_limit_write)
async def preview_import(
    request: Request,
    business_id: uuid.UUID,
    data_type: ImportDataType,
    file: UploadFile,
    _actor: User = Depends(require_business_role(*_can_write)),
) -> PreviewResponse:
    module = _IMPORTER_MODULES[data_type]
    content = await _read_upload(file)
    headers, rows = parse_csv(content)
    return PreviewResponse(
        headers=headers,
        sample_rows=rows[:5],
        canonical_fields=module.CANONICAL_FIELDS,
        required_fields=module.REQUIRED_FIELDS,
        row_count=len(rows),
    )


@router.post("/{data_type}", response_model=ImportSummaryResponse)
@limiter.limit(settings.rate_limit_write)
async def run_import(
    request: Request,
    business_id: uuid.UUID,
    data_type: ImportDataType,
    file: UploadFile,
    column_mapping: str = Form(...),
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> ImportSummaryResponse:
    mapping = _parse_column_mapping(column_mapping)
    content = await _read_upload(file)
    _headers, rows = parse_csv(content)

    summary = await _execute_import(uow, data_type, business_id, rows, mapping)

    return ImportSummaryResponse.from_domain(summary)


@router.post("/{data_type}/jobs", response_model=ImportJobResponse, status_code=202)
@limiter.limit(settings.rate_limit_write)
async def start_import_job(
    request: Request,
    business_id: uuid.UUID,
    data_type: ImportDataType,
    file: UploadFile,
    column_mapping: str = Form(...),
    _actor: User = Depends(require_business_role(*_can_write)),
    registry: ImportJobRegistry = Depends(get_import_job_registry),
) -> ImportJobResponse:
    """Starts the import in the background and returns at once; poll
    GET /imports/jobs/{job_id} for progress. Same validation as the blocking
    endpoint, done up front so a bad file still fails fast with a 422.
    """
    mapping = _parse_column_mapping(column_mapping)
    content = await _read_upload(file)
    _headers, rows = parse_csv(content)

    if registry.running_for_business(business_id) is not None:
        raise HTTPException(
            status_code=409, detail="An import is already running for this business. Wait for it to finish."
        )

    session_factory = get_container().session_factory

    async def run(on_progress: ProgressCallback) -> ImportSummary:
        # The request's session is closed once this response is sent, so the
        # background task opens its own.
        async with session_factory() as session:
            return await _execute_import(
                AppUnitOfWork(session), data_type, business_id, rows, mapping, on_progress
            )

    job = registry.start(business_id=business_id, total_rows=len(rows), runner=run)
    return ImportJobResponse.from_job(job)


@router.get("/jobs/{job_id}", response_model=ImportJobResponse)
async def get_import_job(
    business_id: uuid.UUID,
    job_id: uuid.UUID,
    _actor: User = Depends(require_business_role(*_can_write)),
    registry: ImportJobRegistry = Depends(get_import_job_registry),
) -> ImportJobResponse:
    job = registry.get(job_id)
    # A job belonging to another business is reported as unknown, not forbidden.
    if job is None or job.business_id != business_id:
        raise HTTPException(
            status_code=404,
            detail="This import is no longer tracked (the server may have restarted). "
            "Rows already imported are kept; upload the file again to finish — duplicates are skipped.",
        )
    return ImportJobResponse.from_job(job)


@router.get("/{data_type}/template")
async def download_import_template(
    business_id: uuid.UUID,
    data_type: ImportDataType,
    _actor: User = Depends(require_business_role()),
) -> Response:
    module = _IMPORTER_MODULES[data_type]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(module.CANONICAL_FIELDS)
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{data_type.value}_template.csv"'},
    )
