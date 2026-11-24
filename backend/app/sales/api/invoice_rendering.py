import uuid

from fastapi import Response

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.domain.exceptions import BusinessNotFoundException
from app.sales.application.invoice_pdf import generate_invoice_pdf
from app.sales.domain.entities import Sale


async def render_invoice_response(
    uow: AppUnitOfWork, business_id: uuid.UUID, sale: Sale, *, inline: bool = False
) -> Response:
    """The invoice PDF for a sale, with its business and customer looked up."""
    business = await uow.businesses.get_by_id(business_id)
    if business is None:
        raise BusinessNotFoundException(f"Business {business_id} not found")
    customer = None
    if sale.customer_id:
        customer = await uow.customers.get_by_id_for_business(sale.customer_id, business_id)
    pdf_bytes = generate_invoice_pdf(business=business, sale=sale, customer=customer)
    safe_number = "".join(c if c.isalnum() or c in "-_" else "-" for c in sale.invoice_number)
    disposition = "inline" if inline else "attachment"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename="invoice-{safe_number}.pdf"'},
    )
