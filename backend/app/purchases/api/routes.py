import uuid

from fastapi import APIRouter, Depends, Request

from app.api.rate_limit import limiter
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.api.dependencies import require_business_role
from app.business.domain.value_objects import BusinessRole
from app.config.settings import get_settings
from app.identity.domain.entities import User
from app.purchases.api.schemas import (
    CreatePurchaseRequest,
    PagedPurchasesResponse,
    PurchaseResponse,
    RecordPurchasePaymentRequest,
)
from app.purchases.application.commands.create_purchase import (
    CreatePurchaseCommand,
    CreatePurchaseLineItemInput,
    CreatePurchaseUseCase,
)
from app.purchases.application.commands.record_payment import (
    RecordPurchasePaymentCommand,
    RecordPurchasePaymentUseCase,
)
from app.purchases.application.commands.void_purchase import VoidPurchaseCommand, VoidPurchaseUseCase
from app.purchases.application.queries.get_purchase import GetPurchaseQuery, GetPurchaseUseCase
from app.purchases.application.queries.list_outstanding_purchases import (
    ListOutstandingPurchasesQuery,
    ListOutstandingPurchasesUseCase,
)
from app.purchases.application.queries.list_purchases import ListPurchasesQuery, ListPurchasesUseCase
from app.shared.application.pagination import PageRequest

router = APIRouter(prefix="/businesses/{business_id}/purchases", tags=["purchases"])

settings = get_settings()

_can_write = (BusinessRole.OWNER, BusinessRole.ADMIN, BusinessRole.ACCOUNTANT)


@router.post("", response_model=PurchaseResponse, status_code=201)
@limiter.limit(settings.rate_limit_write)
async def create_purchase(
    request: Request,
    business_id: uuid.UUID,
    body: CreatePurchaseRequest,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PurchaseResponse:
    use_case = CreatePurchaseUseCase(uow)
    purchase = await use_case.execute(
        CreatePurchaseCommand(
            business_id=business_id,
            purchase_number=body.purchase_number,
            vendor_id=body.vendor_id,
            purchase_date=body.purchase_date,
            due_date=body.due_date,
            line_items=[
                CreatePurchaseLineItemInput(
                    line_number=item.line_number,
                    description=item.description,
                    quantity=item.quantity,
                    unit_cost=item.unit_cost,
                    product_id=item.product_id,
                )
                for item in body.line_items
            ],
            tax=body.tax,
            notes=body.notes,
        )
    )
    return PurchaseResponse.from_domain(purchase)


@router.get("", response_model=PagedPurchasesResponse)
async def list_purchases(
    business_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PagedPurchasesResponse:
    use_case = ListPurchasesUseCase(uow)
    page = await use_case.execute(
        ListPurchasesQuery(business_id=business_id, page=PageRequest(offset=offset, limit=limit))
    )
    return PagedPurchasesResponse(
        items=[PurchaseResponse.from_domain(p) for p in page.items],
        total=page.total,
        offset=page.offset,
        limit=page.limit,
    )


@router.get("/outstanding", response_model=list[PurchaseResponse])
async def list_outstanding_purchases(
    business_id: uuid.UUID,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> list[PurchaseResponse]:
    """Registered before /{purchase_id} — see the identical note in
    sales/api/routes.py:list_outstanding_sales.
    """
    use_case = ListOutstandingPurchasesUseCase(uow)
    purchases = await use_case.execute(ListOutstandingPurchasesQuery(business_id=business_id))
    return [PurchaseResponse.from_domain(p) for p in purchases]


@router.get("/{purchase_id}", response_model=PurchaseResponse)
async def get_purchase(
    business_id: uuid.UUID,
    purchase_id: uuid.UUID,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PurchaseResponse:
    use_case = GetPurchaseUseCase(uow)
    purchase = await use_case.execute(GetPurchaseQuery(business_id=business_id, purchase_id=purchase_id))
    return PurchaseResponse.from_domain(purchase)


@router.post("/{purchase_id}/payments", response_model=PurchaseResponse)
@limiter.limit(settings.rate_limit_write)
async def record_purchase_payment(
    request: Request,
    business_id: uuid.UUID,
    purchase_id: uuid.UUID,
    body: RecordPurchasePaymentRequest,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PurchaseResponse:
    use_case = RecordPurchasePaymentUseCase(uow)
    purchase = await use_case.execute(
        RecordPurchasePaymentCommand(business_id=business_id, purchase_id=purchase_id, amount=body.amount)
    )
    return PurchaseResponse.from_domain(purchase)


@router.post("/{purchase_id}/void", response_model=PurchaseResponse)
@limiter.limit(settings.rate_limit_write)
async def void_purchase(
    request: Request,
    business_id: uuid.UUID,
    purchase_id: uuid.UUID,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PurchaseResponse:
    use_case = VoidPurchaseUseCase(uow)
    purchase = await use_case.execute(VoidPurchaseCommand(business_id=business_id, purchase_id=purchase_id))
    return PurchaseResponse.from_domain(purchase)
