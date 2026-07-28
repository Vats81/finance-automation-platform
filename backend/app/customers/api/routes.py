import uuid

from fastapi import APIRouter, Depends, Request

from app.api.rate_limit import limiter
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.api.dependencies import require_business_role
from app.business.domain.value_objects import BusinessRole
from app.config.settings import get_settings
from app.customers.api.schemas import (
    CreateCustomerRequest,
    CustomerResponse,
    PagedCustomersResponse,
    UpdateCustomerRequest,
)
from app.customers.application.commands.create_customer import CreateCustomerCommand, CreateCustomerUseCase
from app.customers.application.commands.deactivate_customer import (
    DeactivateCustomerCommand,
    DeactivateCustomerUseCase,
)
from app.customers.application.commands.reactivate_customer import (
    ReactivateCustomerCommand,
    ReactivateCustomerUseCase,
)
from app.customers.application.commands.update_customer import UpdateCustomerCommand, UpdateCustomerUseCase
from app.customers.application.queries.get_customer import GetCustomerQuery, GetCustomerUseCase
from app.customers.application.queries.list_customers import ListCustomersQuery, ListCustomersUseCase
from app.identity.domain.entities import User
from app.shared.application.pagination import PageRequest

router = APIRouter(prefix="/businesses/{business_id}/customers", tags=["customers"])

settings = get_settings()

_can_write = (BusinessRole.OWNER, BusinessRole.ADMIN, BusinessRole.ACCOUNTANT)


@router.post("", response_model=CustomerResponse, status_code=201)
@limiter.limit(settings.rate_limit_write)
async def create_customer(
    request: Request,
    business_id: uuid.UUID,
    body: CreateCustomerRequest,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> CustomerResponse:
    use_case = CreateCustomerUseCase(uow)
    customer = await use_case.execute(
        CreateCustomerCommand(
            business_id=business_id,
            name=body.name,
            phone=body.phone,
            email=body.email,
            street=body.address.street if body.address else None,
            city=body.address.city if body.address else None,
            state=body.address.state if body.address else None,
            postal_code=body.address.postal_code if body.address else None,
            country=body.address.country if body.address else "US",
            gst_number=body.gst_number,
        )
    )
    return CustomerResponse.from_domain(customer)


@router.get("", response_model=PagedCustomersResponse)
async def list_customers(
    business_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PagedCustomersResponse:
    use_case = ListCustomersUseCase(uow)
    page = await use_case.execute(
        ListCustomersQuery(business_id=business_id, page=PageRequest(offset=offset, limit=limit))
    )
    return PagedCustomersResponse(
        items=[CustomerResponse.from_domain(c) for c in page.items],
        total=page.total,
        offset=page.offset,
        limit=page.limit,
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    business_id: uuid.UUID,
    customer_id: uuid.UUID,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> CustomerResponse:
    use_case = GetCustomerUseCase(uow)
    customer = await use_case.execute(GetCustomerQuery(business_id=business_id, customer_id=customer_id))
    return CustomerResponse.from_domain(customer)


@router.patch("/{customer_id}", response_model=CustomerResponse)
@limiter.limit(settings.rate_limit_write)
async def update_customer(
    request: Request,
    business_id: uuid.UUID,
    customer_id: uuid.UUID,
    body: UpdateCustomerRequest,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> CustomerResponse:
    use_case = UpdateCustomerUseCase(uow)
    customer = await use_case.execute(
        UpdateCustomerCommand(
            business_id=business_id,
            customer_id=customer_id,
            name=body.name,
            phone=body.phone,
            email=body.email,
            street=body.address.street if body.address else None,
            city=body.address.city if body.address else None,
            state=body.address.state if body.address else None,
            postal_code=body.address.postal_code if body.address else None,
            country=body.address.country if body.address else None,
            gst_number=body.gst_number,
        )
    )
    return CustomerResponse.from_domain(customer)


@router.post("/{customer_id}/deactivate", response_model=CustomerResponse)
@limiter.limit(settings.rate_limit_write)
async def deactivate_customer(
    request: Request,
    business_id: uuid.UUID,
    customer_id: uuid.UUID,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> CustomerResponse:
    use_case = DeactivateCustomerUseCase(uow)
    customer = await use_case.execute(
        DeactivateCustomerCommand(business_id=business_id, customer_id=customer_id)
    )
    return CustomerResponse.from_domain(customer)


@router.post("/{customer_id}/reactivate", response_model=CustomerResponse)
@limiter.limit(settings.rate_limit_write)
async def reactivate_customer(
    request: Request,
    business_id: uuid.UUID,
    customer_id: uuid.UUID,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> CustomerResponse:
    use_case = ReactivateCustomerUseCase(uow)
    customer = await use_case.execute(
        ReactivateCustomerCommand(business_id=business_id, customer_id=customer_id)
    )
    return CustomerResponse.from_domain(customer)
