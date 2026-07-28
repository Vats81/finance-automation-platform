import uuid

from fastapi import APIRouter, Depends, Request

from app.api.rate_limit import limiter
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.api.dependencies import require_business_role
from app.business.domain.value_objects import BusinessRole
from app.config.settings import get_settings
from app.identity.domain.entities import User
from app.shared.application.pagination import PageRequest
from app.vendors.api.schemas import (
    CreateVendorRequest,
    PagedVendorsResponse,
    UpdateVendorRequest,
    VendorResponse,
)
from app.vendors.application.commands.create_business_vendor import (
    CreateBusinessVendorCommand,
    CreateBusinessVendorUseCase,
)
from app.vendors.application.commands.update_business_vendor import (
    UpdateBusinessVendorCommand,
    UpdateBusinessVendorUseCase,
)
from app.vendors.application.queries.get_business_vendor import (
    GetBusinessVendorQuery,
    GetBusinessVendorUseCase,
)
from app.vendors.application.queries.list_business_vendors import (
    ListBusinessVendorsQuery,
    ListBusinessVendorsUseCase,
)

router = APIRouter(prefix="/businesses/{business_id}/vendors", tags=["business-vendors"])

settings = get_settings()

# Vendor onboarding for the SMB product is open to any role that can touch
# money on the business's behalf; VIEWER is read-only.
_can_write = (BusinessRole.OWNER, BusinessRole.ADMIN, BusinessRole.ACCOUNTANT)


@router.post("", response_model=VendorResponse, status_code=201)
@limiter.limit(settings.rate_limit_write)
async def create_business_vendor(
    request: Request,
    business_id: uuid.UUID,
    body: CreateVendorRequest,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> VendorResponse:
    use_case = CreateBusinessVendorUseCase(uow)
    vendor = await use_case.execute(
        CreateBusinessVendorCommand(
            business_id=business_id,
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
async def list_business_vendors(
    business_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PagedVendorsResponse:
    use_case = ListBusinessVendorsUseCase(uow)
    page = await use_case.execute(
        ListBusinessVendorsQuery(business_id=business_id, page=PageRequest(offset=offset, limit=limit))
    )
    return PagedVendorsResponse(
        items=[VendorResponse.from_domain(v) for v in page.items],
        total=page.total,
        offset=page.offset,
        limit=page.limit,
    )


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_business_vendor(
    business_id: uuid.UUID,
    vendor_id: uuid.UUID,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> VendorResponse:
    use_case = GetBusinessVendorUseCase(uow)
    vendor = await use_case.execute(GetBusinessVendorQuery(business_id=business_id, vendor_id=vendor_id))
    return VendorResponse.from_domain(vendor)


@router.patch("/{vendor_id}", response_model=VendorResponse)
@limiter.limit(settings.rate_limit_write)
async def update_business_vendor(
    request: Request,
    business_id: uuid.UUID,
    vendor_id: uuid.UUID,
    body: UpdateVendorRequest,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> VendorResponse:
    use_case = UpdateBusinessVendorUseCase(uow)
    vendor = await use_case.execute(
        UpdateBusinessVendorCommand(
            business_id=business_id,
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
