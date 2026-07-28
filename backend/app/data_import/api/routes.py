import csv
import io
import json
import uuid

from fastapi import APIRouter, Depends, Form, Request, UploadFile
from fastapi.responses import Response

from app.api.rate_limit import limiter
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.api.dependencies import require_business_role
from app.business.domain.value_objects import BusinessRole
from app.config.settings import get_settings
from app.data_import.api.schemas import ImportDataType, ImportSummaryResponse, PreviewResponse
from app.data_import.application import import_customers, import_expenses, import_products, import_vendors
from app.identity.domain.entities import User
from app.shared.infrastructure.csv_parser import parse_csv

router = APIRouter(prefix="/businesses/{business_id}/imports", tags=["data-import"])

settings = get_settings()

_can_write = (BusinessRole.OWNER, BusinessRole.ADMIN, BusinessRole.ACCOUNTANT)

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
    content = await file.read()
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
    content = await file.read()
    _headers, rows = parse_csv(content)
    mapping: dict[str, str] = json.loads(column_mapping)

    if data_type == ImportDataType.CUSTOMERS:
        summary = await import_customers.ImportCustomersUseCase(uow).execute(
            business_id=business_id, rows=rows, column_mapping=mapping
        )
    elif data_type == ImportDataType.VENDORS:
        summary = await import_vendors.ImportVendorsUseCase(uow).execute(
            business_id=business_id, rows=rows, column_mapping=mapping
        )
    elif data_type == ImportDataType.PRODUCTS:
        summary = await import_products.ImportProductsUseCase(uow).execute(
            business_id=business_id, rows=rows, column_mapping=mapping
        )
    else:
        summary = await import_expenses.ImportExpensesUseCase(uow).execute(
            business_id=business_id, rows=rows, column_mapping=mapping
        )

    return ImportSummaryResponse.from_domain(summary)


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
