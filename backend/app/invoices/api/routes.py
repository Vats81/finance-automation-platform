import io
import uuid

from fastapi import APIRouter, Depends, Request, UploadFile

from app.api.rate_limit import limiter
from app.bootstrap.container import get_file_storage, get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.config.settings import get_settings
from app.identity.api.dependencies import get_current_user
from app.identity.domain.entities import User
from app.invoices.api.dependencies import require_invoice_writer
from app.invoices.api.schemas import InvoiceResponse, PagedInvoicesResponse, SubmitInvoiceRequest
from app.invoices.application.commands.attach_document import AttachDocumentCommand, AttachDocumentUseCase
from app.invoices.application.commands.submit_invoice import (
    SubmitInvoiceCommand,
    SubmitInvoiceLineItemInput,
    SubmitInvoiceUseCase,
)
from app.invoices.application.queries.get_invoice import GetInvoiceQuery, GetInvoiceUseCase
from app.invoices.application.queries.list_invoices import ListInvoicesQuery, ListInvoicesUseCase
from app.shared.application.pagination import PageRequest
from app.shared.application.ports import IFileStorage

router = APIRouter(prefix="/invoices", tags=["invoices"])

settings = get_settings()


@router.post("", response_model=InvoiceResponse, status_code=201)
@limiter.limit(settings.rate_limit_write)
async def submit_invoice(
    request: Request,
    body: SubmitInvoiceRequest,
    _actor: User = Depends(require_invoice_writer),
    uow: AppUnitOfWork = Depends(get_uow),
) -> InvoiceResponse:
    use_case = SubmitInvoiceUseCase(uow)
    invoice = await use_case.execute(
        SubmitInvoiceCommand(
            invoice_number=body.invoice_number,
            vendor_id=body.vendor_id,
            po_id=body.po_id,
            line_items=[
                SubmitInvoiceLineItemInput(
                    line_number=item.line_number,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                )
                for item in body.line_items
            ],
        )
    )
    return InvoiceResponse.from_domain(invoice)


@router.get("", response_model=PagedInvoicesResponse)
async def list_invoices(
    offset: int = 0,
    limit: int = 50,
    _actor: User = Depends(get_current_user),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PagedInvoicesResponse:
    use_case = ListInvoicesUseCase(uow)
    page = await use_case.execute(ListInvoicesQuery(page=PageRequest(offset=offset, limit=limit)))
    return PagedInvoicesResponse(
        items=[InvoiceResponse.from_domain(inv) for inv in page.items],
        total=page.total,
        offset=page.offset,
        limit=page.limit,
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: uuid.UUID,
    _actor: User = Depends(get_current_user),
    uow: AppUnitOfWork = Depends(get_uow),
) -> InvoiceResponse:
    use_case = GetInvoiceUseCase(uow)
    invoice = await use_case.execute(GetInvoiceQuery(invoice_id=invoice_id))
    return InvoiceResponse.from_domain(invoice)


@router.post("/{invoice_id}/document", response_model=InvoiceResponse)
@limiter.limit(settings.rate_limit_write)
async def attach_document(
    request: Request,
    invoice_id: uuid.UUID,
    file: UploadFile,
    _actor: User = Depends(require_invoice_writer),
    uow: AppUnitOfWork = Depends(get_uow),
    file_storage: IFileStorage = Depends(get_file_storage),
) -> InvoiceResponse:
    use_case = AttachDocumentUseCase(uow, file_storage, settings.azure_storage_container_name)
    content = io.BytesIO(await file.read())
    invoice = await use_case.execute(
        AttachDocumentCommand(
            invoice_id=invoice_id,
            filename=file.filename or "invoice.pdf",
            content=content,
            content_type=file.content_type or "application/octet-stream",
        )
    )
    return InvoiceResponse.from_domain(invoice)
