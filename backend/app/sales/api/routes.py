import uuid

from fastapi import APIRouter, Depends, Request

from app.api.rate_limit import limiter
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.api.dependencies import require_business_role
from app.business.domain.value_objects import BusinessRole
from app.config.settings import get_settings
from app.identity.domain.entities import User
from app.sales.api.schemas import (
    CreateSaleRequest,
    PagedSalesResponse,
    RecordSalePaymentRequest,
    SaleResponse,
)
from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
from app.sales.application.commands.record_payment import RecordSalePaymentCommand, RecordSalePaymentUseCase
from app.sales.application.commands.void_sale import VoidSaleCommand, VoidSaleUseCase
from app.sales.application.queries.get_sale import GetSaleQuery, GetSaleUseCase
from app.sales.application.queries.list_outstanding_sales import (
    ListOutstandingSalesQuery,
    ListOutstandingSalesUseCase,
)
from app.sales.application.queries.list_sales import ListSalesQuery, ListSalesUseCase
from app.shared.application.pagination import PageRequest

router = APIRouter(prefix="/businesses/{business_id}/sales", tags=["sales"])

settings = get_settings()

_can_write = (BusinessRole.OWNER, BusinessRole.ADMIN, BusinessRole.ACCOUNTANT)


@router.post("", response_model=SaleResponse, status_code=201)
@limiter.limit(settings.rate_limit_write)
async def create_sale(
    request: Request,
    business_id: uuid.UUID,
    body: CreateSaleRequest,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> SaleResponse:
    use_case = CreateSaleUseCase(uow)
    sale = await use_case.execute(
        CreateSaleCommand(
            business_id=business_id,
            invoice_number=body.invoice_number,
            invoice_date=body.invoice_date,
            due_date=body.due_date,
            customer_id=body.customer_id,
            line_items=[
                CreateSaleLineItemInput(
                    line_number=item.line_number,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                )
                for item in body.line_items
            ],
            discount=body.discount,
            tax=body.tax,
            notes=body.notes,
        )
    )
    return SaleResponse.from_domain(sale)


@router.get("", response_model=PagedSalesResponse)
async def list_sales(
    business_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PagedSalesResponse:
    use_case = ListSalesUseCase(uow)
    page = await use_case.execute(
        ListSalesQuery(business_id=business_id, page=PageRequest(offset=offset, limit=limit))
    )
    return PagedSalesResponse(
        items=[SaleResponse.from_domain(s) for s in page.items],
        total=page.total,
        offset=page.offset,
        limit=page.limit,
    )


@router.get("/outstanding", response_model=list[SaleResponse])
async def list_outstanding_sales(
    business_id: uuid.UUID,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> list[SaleResponse]:
    """Registered before /{sale_id} — Starlette matches routes in
    registration order, and 'outstanding' would otherwise be swallowed by
    the /{sale_id}: uuid.UUID route and rejected as an invalid UUID (422).
    """
    use_case = ListOutstandingSalesUseCase(uow)
    sales = await use_case.execute(ListOutstandingSalesQuery(business_id=business_id))
    return [SaleResponse.from_domain(s) for s in sales]


@router.get("/{sale_id}", response_model=SaleResponse)
async def get_sale(
    business_id: uuid.UUID,
    sale_id: uuid.UUID,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> SaleResponse:
    use_case = GetSaleUseCase(uow)
    sale = await use_case.execute(GetSaleQuery(business_id=business_id, sale_id=sale_id))
    return SaleResponse.from_domain(sale)


@router.post("/{sale_id}/payments", response_model=SaleResponse)
@limiter.limit(settings.rate_limit_write)
async def record_sale_payment(
    request: Request,
    business_id: uuid.UUID,
    sale_id: uuid.UUID,
    body: RecordSalePaymentRequest,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> SaleResponse:
    use_case = RecordSalePaymentUseCase(uow)
    sale = await use_case.execute(
        RecordSalePaymentCommand(business_id=business_id, sale_id=sale_id, amount=body.amount)
    )
    return SaleResponse.from_domain(sale)


@router.post("/{sale_id}/void", response_model=SaleResponse)
@limiter.limit(settings.rate_limit_write)
async def void_sale(
    request: Request,
    business_id: uuid.UUID,
    sale_id: uuid.UUID,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> SaleResponse:
    use_case = VoidSaleUseCase(uow)
    sale = await use_case.execute(VoidSaleCommand(business_id=business_id, sale_id=sale_id))
    return SaleResponse.from_domain(sale)
