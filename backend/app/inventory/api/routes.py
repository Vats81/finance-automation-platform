import uuid

from fastapi import APIRouter, Depends, Request

from app.api.rate_limit import limiter
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.api.dependencies import require_business_role
from app.business.domain.value_objects import BusinessRole
from app.config.settings import get_settings
from app.identity.domain.entities import User
from app.inventory.api.schemas import (
    AdjustStockRequest,
    CreateProductRequest,
    PagedProductsResponse,
    ProductResponse,
    UpdateProductRequest,
)
from app.inventory.application.commands.adjust_stock import AdjustStockCommand, AdjustStockUseCase
from app.inventory.application.commands.create_product import CreateProductCommand, CreateProductUseCase
from app.inventory.application.commands.deactivate_product import (
    DeactivateProductCommand,
    DeactivateProductUseCase,
)
from app.inventory.application.commands.reactivate_product import (
    ReactivateProductCommand,
    ReactivateProductUseCase,
)
from app.inventory.application.commands.update_product import UpdateProductCommand, UpdateProductUseCase
from app.inventory.application.queries.get_product import GetProductQuery, GetProductUseCase
from app.inventory.application.queries.list_products import ListProductsQuery, ListProductsUseCase
from app.shared.application.pagination import PageRequest

router = APIRouter(prefix="/businesses/{business_id}/products", tags=["inventory"])

settings = get_settings()

_can_write = (BusinessRole.OWNER, BusinessRole.ADMIN, BusinessRole.ACCOUNTANT)


@router.post("", response_model=ProductResponse, status_code=201)
@limiter.limit(settings.rate_limit_write)
async def create_product(
    request: Request,
    business_id: uuid.UUID,
    body: CreateProductRequest,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> ProductResponse:
    use_case = CreateProductUseCase(uow)
    product = await use_case.execute(
        CreateProductCommand(
            business_id=business_id,
            name=body.name,
            sku=body.sku,
            selling_price=body.selling_price,
            purchase_cost=body.purchase_cost,
            category=body.category,
            current_quantity=body.current_quantity,
            minimum_stock_level=body.minimum_stock_level,
            reorder_quantity=body.reorder_quantity,
            unit_of_measurement=body.unit_of_measurement,
            vendor_id=body.vendor_id,
        )
    )
    return ProductResponse.from_domain(product)


@router.get("", response_model=PagedProductsResponse)
async def list_products(
    business_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PagedProductsResponse:
    use_case = ListProductsUseCase(uow)
    page = await use_case.execute(
        ListProductsQuery(business_id=business_id, page=PageRequest(offset=offset, limit=limit))
    )
    return PagedProductsResponse(
        items=[ProductResponse.from_domain(p) for p in page.items],
        total=page.total,
        offset=page.offset,
        limit=page.limit,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    business_id: uuid.UUID,
    product_id: uuid.UUID,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> ProductResponse:
    use_case = GetProductUseCase(uow)
    product = await use_case.execute(GetProductQuery(business_id=business_id, product_id=product_id))
    return ProductResponse.from_domain(product)


@router.patch("/{product_id}", response_model=ProductResponse)
@limiter.limit(settings.rate_limit_write)
async def update_product(
    request: Request,
    business_id: uuid.UUID,
    product_id: uuid.UUID,
    body: UpdateProductRequest,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> ProductResponse:
    use_case = UpdateProductUseCase(uow)
    product = await use_case.execute(
        UpdateProductCommand(
            business_id=business_id,
            product_id=product_id,
            name=body.name,
            category=body.category,
            selling_price=body.selling_price,
            purchase_cost=body.purchase_cost,
            minimum_stock_level=body.minimum_stock_level,
            reorder_quantity=body.reorder_quantity,
        )
    )
    return ProductResponse.from_domain(product)


@router.post("/{product_id}/adjust-stock", response_model=ProductResponse)
@limiter.limit(settings.rate_limit_write)
async def adjust_stock(
    request: Request,
    business_id: uuid.UUID,
    product_id: uuid.UUID,
    body: AdjustStockRequest,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> ProductResponse:
    use_case = AdjustStockUseCase(uow)
    product = await use_case.execute(
        AdjustStockCommand(
            business_id=business_id, product_id=product_id, delta=body.delta, reason=body.reason
        )
    )
    return ProductResponse.from_domain(product)


@router.post("/{product_id}/deactivate", response_model=ProductResponse)
@limiter.limit(settings.rate_limit_write)
async def deactivate_product(
    request: Request,
    business_id: uuid.UUID,
    product_id: uuid.UUID,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> ProductResponse:
    use_case = DeactivateProductUseCase(uow)
    product = await use_case.execute(
        DeactivateProductCommand(business_id=business_id, product_id=product_id)
    )
    return ProductResponse.from_domain(product)


@router.post("/{product_id}/reactivate", response_model=ProductResponse)
@limiter.limit(settings.rate_limit_write)
async def reactivate_product(
    request: Request,
    business_id: uuid.UUID,
    product_id: uuid.UUID,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> ProductResponse:
    use_case = ReactivateProductUseCase(uow)
    product = await use_case.execute(
        ReactivateProductCommand(business_id=business_id, product_id=product_id)
    )
    return ProductResponse.from_domain(product)
