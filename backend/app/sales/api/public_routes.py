from fastapi import APIRouter, Depends, Request, Response

from app.api.rate_limit import limiter
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.domain.value_objects import BusinessStatus
from app.sales.api.invoice_rendering import render_invoice_response
from app.sales.application.commands.share_invoice import ResolveInvoiceShareLinkUseCase
from app.sales.domain.exceptions import InvoiceLinkNotFoundException

router = APIRouter(prefix="/public/invoices", tags=["public"])

# Open to anyone holding the link (no sign-in), so rate limited. The token is 192 bits and only its hash is
# stored, so guessing one is not feasible; the limit is there to keep scrapers and loops cheap.
_PUBLIC_RATE_LIMIT = "60/minute"


@router.get("/{token}")
@limiter.limit(_PUBLIC_RATE_LIMIT)
async def open_shared_invoice(
    request: Request,
    token: str,
    uow: AppUnitOfWork = Depends(get_uow),
) -> Response:
    sale = await ResolveInvoiceShareLinkUseCase(uow).execute(token)
    business = await uow.businesses.get_by_id(sale.business_id)
    if business is None or business.status != BusinessStatus.ACTIVE:
        raise InvoiceLinkNotFoundException("This invoice link is not valid.")
    response = await render_invoice_response(uow, sale.business_id, sale, inline=True)
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
