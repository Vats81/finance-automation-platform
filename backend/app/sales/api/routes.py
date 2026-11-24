import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Request, Response

from app.api.rate_limit import limiter
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.api.dependencies import require_business_role
from app.business.api.permissions import CAN_WRITE
from app.config.settings import get_settings
from app.identity.domain.entities import User
from app.sales.api.invoice_rendering import render_invoice_response
from app.sales.api.schemas import (
    CreateSaleRequest,
    NextInvoiceNumberResponse,
    PagedSalesResponse,
    ReceivableCustomerSchema,
    ReceivableInvoiceSchema,
    ReceivablesResponse,
    RecordSalePaymentRequest,
    RevokeShareLinksResponse,
    SaleResponse,
    ShareLinkResponse,
    UpdateSaleRequest,
)
from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
from app.sales.application.commands.record_payment import RecordSalePaymentCommand, RecordSalePaymentUseCase
from app.sales.application.commands.share_invoice import (
    CreateInvoiceShareLinkCommand,
    CreateInvoiceShareLinkUseCase,
    RevokeInvoiceShareLinksCommand,
    RevokeInvoiceShareLinksUseCase,
)
from app.sales.application.commands.update_sale import (
    UpdateSaleCommand,
    UpdateSaleLineItemInput,
    UpdateSaleUseCase,
)
from app.sales.application.commands.void_sale import VoidSaleCommand, VoidSaleUseCase
from app.sales.application.queries.get_receivables import GetReceivablesQuery, GetReceivablesUseCase
from app.sales.application.queries.get_sale import GetSaleQuery, GetSaleUseCase
from app.sales.application.queries.list_outstanding_sales import (
    ListOutstandingSalesQuery,
    ListOutstandingSalesUseCase,
)
from app.sales.application.queries.list_sales import ListSalesQuery, ListSalesUseCase
from app.sales.application.queries.next_invoice_number import (
    NextInvoiceNumberQuery,
    NextInvoiceNumberUseCase,
)
from app.shared.application.pagination import PageRequest

router = APIRouter(prefix="/businesses/{business_id}/sales", tags=["sales"])

settings = get_settings()

_can_write = CAN_WRITE


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
                    gst_rate=item.gst_rate,
                    hsn_code=item.hsn_code,
                )
                for item in body.line_items
            ],
            discount=body.discount,
            tax=body.tax,
            notes=body.notes,
            place_of_supply=body.place_of_supply,
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


@router.get("/next-invoice-number", response_model=NextInvoiceNumberResponse)
async def get_next_invoice_number(
    business_id: uuid.UUID,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> NextInvoiceNumberResponse:
    """The next number in this business's invoice series (registered before /{sale_id}, like /outstanding)."""
    number = await NextInvoiceNumberUseCase(uow).execute(NextInvoiceNumberQuery(business_id=business_id))
    return NextInvoiceNumberResponse(invoice_number=number)


@router.get("/receivables", response_model=ReceivablesResponse)
async def get_receivables(
    business_id: uuid.UUID,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> ReceivablesResponse:
    """Who owes the business money (the udhaar list), by customer, largest first."""
    groups = await GetReceivablesUseCase(uow).execute(
        GetReceivablesQuery(business_id=business_id, today=date.today())
    )
    customers, _ = await uow.customers.list_for_business(business_id, offset=0, limit=10_000)
    by_id = {c.id: c for c in customers}
    rows = []
    for group in groups:
        customer = by_id.get(group.customer_id) if group.customer_id else None
        rows.append(
            ReceivableCustomerSchema(
                customer_id=group.customer_id,
                name=customer.name if customer else "Walk-in customers",
                phone=customer.phone if customer else None,
                outstanding=group.outstanding,
                days_overdue=group.days_overdue,
                invoices=[
                    ReceivableInvoiceSchema(
                        sale_id=i.sale_id,
                        invoice_number=i.invoice_number,
                        invoice_date=i.invoice_date,
                        due_date=i.due_date,
                        outstanding=i.outstanding,
                        days_overdue=i.days_overdue,
                    )
                    for i in group.invoices
                ],
            )
        )
    total = sum((g.outstanding for g in groups), Decimal("0"))
    return ReceivablesResponse(total_outstanding=total, customers=rows)


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


@router.get("/{sale_id}/invoice-pdf")
async def get_sale_invoice_pdf(
    business_id: uuid.UUID,
    sale_id: uuid.UUID,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> Response:
    """The printable invoice (a GST tax invoice when the lines carry GST rates)."""
    sale = await GetSaleUseCase(uow).execute(GetSaleQuery(business_id=business_id, sale_id=sale_id))
    return await render_invoice_response(uow, business_id, sale)


@router.post("/{sale_id}/share-link", response_model=ShareLinkResponse, status_code=201)
@limiter.limit(settings.rate_limit_write)
async def create_invoice_share_link(
    request: Request,
    business_id: uuid.UUID,
    sale_id: uuid.UUID,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> ShareLinkResponse:
    """A private link to the invoice's PDF, for sending to the customer (for example on WhatsApp)."""
    link, token = await CreateInvoiceShareLinkUseCase(uow).execute(
        CreateInvoiceShareLinkCommand(business_id=business_id, sale_id=sale_id)
    )
    base = settings.frontend_base_url.rstrip("/")
    return ShareLinkResponse(url=f"{base}/i/{token}", expires_at=link.expires_at)


@router.post("/{sale_id}/share-link/revoke", response_model=RevokeShareLinksResponse)
@limiter.limit(settings.rate_limit_write)
async def revoke_invoice_share_links(
    request: Request,
    business_id: uuid.UUID,
    sale_id: uuid.UUID,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> RevokeShareLinksResponse:
    revoked = await RevokeInvoiceShareLinksUseCase(uow).execute(
        RevokeInvoiceShareLinksCommand(business_id=business_id, sale_id=sale_id)
    )
    return RevokeShareLinksResponse(revoked=revoked)


@router.patch("/{sale_id}", response_model=SaleResponse)
@limiter.limit(settings.rate_limit_write)
async def update_sale(
    request: Request,
    business_id: uuid.UUID,
    sale_id: uuid.UUID,
    body: UpdateSaleRequest,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> SaleResponse:
    use_case = UpdateSaleUseCase(uow)
    sale = await use_case.execute(
        UpdateSaleCommand(
            business_id=business_id,
            sale_id=sale_id,
            invoice_number=body.invoice_number,
            invoice_date=body.invoice_date,
            due_date=body.due_date,
            customer_id=body.customer_id,
            line_items=[
                UpdateSaleLineItemInput(
                    line_number=item.line_number,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    gst_rate=item.gst_rate,
                    hsn_code=item.hsn_code,
                )
                for item in body.line_items
            ],
            discount=body.discount,
            tax=body.tax,
            notes=body.notes,
            place_of_supply=body.place_of_supply,
        )
    )
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
