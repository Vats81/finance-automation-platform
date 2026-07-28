import uuid

from fastapi import APIRouter, Depends, Request

from app.api.rate_limit import limiter
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.config.settings import get_settings
from app.identity.api.dependencies import get_current_user
from app.identity.domain.entities import User
from app.purchase_orders.api.dependencies import require_po_writer
from app.purchase_orders.api.schemas import (
    CreatePurchaseOrderRequest,
    PagedPurchaseOrdersResponse,
    PurchaseOrderResponse,
)
from app.purchase_orders.application.commands.create_purchase_order import (
    CreatePurchaseOrderCommand,
    CreatePurchaseOrderUseCase,
    LineItemInput,
)
from app.purchase_orders.application.queries.get_purchase_order import (
    GetPurchaseOrderQuery,
    GetPurchaseOrderUseCase,
)
from app.purchase_orders.application.queries.list_purchase_orders import (
    ListPurchaseOrdersQuery,
    ListPurchaseOrdersUseCase,
)
from app.shared.application.pagination import PageRequest

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])

settings = get_settings()


@router.post("", response_model=PurchaseOrderResponse, status_code=201)
@limiter.limit(settings.rate_limit_write)
async def create_purchase_order(
    request: Request,
    body: CreatePurchaseOrderRequest,
    _actor: User = Depends(require_po_writer),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PurchaseOrderResponse:
    use_case = CreatePurchaseOrderUseCase(uow)
    po = await use_case.execute(
        CreatePurchaseOrderCommand(
            vendor_id=body.vendor_id,
            line_items=[
                LineItemInput(
                    line_number=item.line_number,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                )
                for item in body.line_items
            ],
        )
    )
    return PurchaseOrderResponse.from_domain(po)


@router.get("", response_model=PagedPurchaseOrdersResponse)
async def list_purchase_orders(
    offset: int = 0,
    limit: int = 50,
    _actor: User = Depends(get_current_user),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PagedPurchaseOrdersResponse:
    use_case = ListPurchaseOrdersUseCase(uow)
    page = await use_case.execute(ListPurchaseOrdersQuery(page=PageRequest(offset=offset, limit=limit)))
    return PagedPurchaseOrdersResponse(
        items=[PurchaseOrderResponse.from_domain(po) for po in page.items],
        total=page.total,
        offset=page.offset,
        limit=page.limit,
    )


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
async def get_purchase_order(
    po_id: uuid.UUID,
    _actor: User = Depends(get_current_user),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PurchaseOrderResponse:
    use_case = GetPurchaseOrderUseCase(uow)
    po = await use_case.execute(GetPurchaseOrderQuery(po_id=po_id))
    return PurchaseOrderResponse.from_domain(po)
