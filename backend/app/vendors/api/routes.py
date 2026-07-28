import io
import uuid

from fastapi import APIRouter, Depends, Request, UploadFile

from app.api.rate_limit import limiter
from app.bootstrap.container import get_file_storage, get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.config.settings import get_settings
from app.identity.api.dependencies import get_current_user
from app.identity.domain.entities import User
from app.shared.application.pagination import PageRequest
from app.shared.application.ports import IFileStorage
from app.vendors.api.dependencies import require_vendor_activator, require_vendor_writer
from app.vendors.api.schemas import (
    CreateVendorRequest,
    PagedVendorsResponse,
    UpdateVendorRequest,
    VendorResponse,
)
from app.vendors.application.commands.activate_vendor import ActivateVendorCommand, ActivateVendorUseCase
from app.vendors.application.commands.create_vendor import CreateVendorCommand, CreateVendorUseCase
from app.vendors.application.commands.update_vendor import UpdateVendorCommand, UpdateVendorUseCase
from app.vendors.application.commands.upload_w9_document import (
    UploadW9DocumentCommand,
    UploadW9DocumentUseCase,
)
from app.vendors.application.queries.get_vendor import GetVendorQuery, GetVendorUseCase
from app.vendors.application.queries.list_vendors import ListVendorsQuery, ListVendorsUseCase

router = APIRouter(prefix="/vendors", tags=["vendors"])

settings = get_settings()


@router.post("", response_model=VendorResponse, status_code=201)
@limiter.limit(settings.rate_limit_write)
async def create_vendor(
    request: Request,
    body: CreateVendorRequest,
    _actor: User = Depends(require_vendor_writer),
    uow: AppUnitOfWork = Depends(get_uow),
) -> VendorResponse:
    use_case = CreateVendorUseCase(uow)
    vendor = await use_case.execute(
        CreateVendorCommand(
            legal_name=body.legal_name,
            contact_email=body.contact_email,
            tax_id=body.tax_id,
            street=body.address.street,
            city=body.address.city,
            state=body.address.state,
            postal_code=body.address.postal_code,
            country=body.address.country,
        )
    )
    return VendorResponse.from_domain(vendor)


@router.get("", response_model=PagedVendorsResponse)
async def list_vendors(
    offset: int = 0,
    limit: int = 50,
    _actor: User = Depends(get_current_user),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PagedVendorsResponse:
    use_case = ListVendorsUseCase(uow)
    page = await use_case.execute(ListVendorsQuery(page=PageRequest(offset=offset, limit=limit)))
    return PagedVendorsResponse(
        items=[VendorResponse.from_domain(v) for v in page.items],
        total=page.total,
        offset=page.offset,
        limit=page.limit,
    )


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: uuid.UUID,
    _actor: User = Depends(get_current_user),
    uow: AppUnitOfWork = Depends(get_uow),
) -> VendorResponse:
    use_case = GetVendorUseCase(uow)
    vendor = await use_case.execute(GetVendorQuery(vendor_id=vendor_id))
    return VendorResponse.from_domain(vendor)


@router.patch("/{vendor_id}", response_model=VendorResponse)
@limiter.limit(settings.rate_limit_write)
async def update_vendor(
    request: Request,
    vendor_id: uuid.UUID,
    body: UpdateVendorRequest,
    _actor: User = Depends(require_vendor_writer),
    uow: AppUnitOfWork = Depends(get_uow),
) -> VendorResponse:
    use_case = UpdateVendorUseCase(uow)
    vendor = await use_case.execute(
        UpdateVendorCommand(
            vendor_id=vendor_id,
            legal_name=body.legal_name,
            contact_email=body.contact_email,
            street=body.address.street if body.address else None,
            city=body.address.city if body.address else None,
            state=body.address.state if body.address else None,
            postal_code=body.address.postal_code if body.address else None,
            country=body.address.country if body.address else None,
        )
    )
    return VendorResponse.from_domain(vendor)


@router.post("/{vendor_id}/w9-document", response_model=VendorResponse)
@limiter.limit(settings.rate_limit_write)
async def upload_w9_document(
    request: Request,
    vendor_id: uuid.UUID,
    file: UploadFile,
    _actor: User = Depends(require_vendor_writer),
    uow: AppUnitOfWork = Depends(get_uow),
    file_storage: IFileStorage = Depends(get_file_storage),
) -> VendorResponse:
    use_case = UploadW9DocumentUseCase(uow, file_storage, settings.azure_storage_container_name)
    content = io.BytesIO(await file.read())
    vendor = await use_case.execute(
        UploadW9DocumentCommand(
            vendor_id=vendor_id,
            filename=file.filename or "w9.pdf",
            content=content,
            content_type=file.content_type or "application/octet-stream",
        )
    )
    return VendorResponse.from_domain(vendor)


@router.post("/{vendor_id}/activate", response_model=VendorResponse)
@limiter.limit(settings.rate_limit_write)
async def activate_vendor(
    request: Request,
    vendor_id: uuid.UUID,
    _actor: User = Depends(require_vendor_activator),
    uow: AppUnitOfWork = Depends(get_uow),
) -> VendorResponse:
    use_case = ActivateVendorUseCase(uow)
    vendor = await use_case.execute(ActivateVendorCommand(vendor_id=vendor_id))
    return VendorResponse.from_domain(vendor)
