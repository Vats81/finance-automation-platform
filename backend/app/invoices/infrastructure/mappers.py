from decimal import Decimal

from app.invoices.domain.entities import Invoice
from app.invoices.domain.value_objects import InvoiceLineItem, InvoiceStatus
from app.invoices.infrastructure.models import InvoiceModel
from app.shared.domain.value_objects import Money


def _line_item_to_dict(item: InvoiceLineItem) -> dict:
    return {
        "line_number": item.line_number,
        "description": item.description,
        "quantity": str(item.quantity),
        "unit_price_cents": item.unit_price.cents,
    }


def _dict_to_line_item(data: dict) -> InvoiceLineItem:
    return InvoiceLineItem(
        line_number=data["line_number"],
        description=data["description"],
        quantity=Decimal(data["quantity"]),
        unit_price=Money.from_cents(data["unit_price_cents"]),
    )


def model_to_domain(model: InvoiceModel) -> Invoice:
    return Invoice(
        entity_id=model.id,
        invoice_number=model.invoice_number,
        vendor_id=model.vendor_id,
        po_id=model.po_id,
        line_items=[_dict_to_line_item(item) for item in model.line_items],
        document_reference=model.document_reference,
        status=InvoiceStatus(model.status),
        match_discrepancies=list(model.match_discrepancies),
        created_at=model.created_at,
    )


def domain_to_model(invoice: Invoice) -> InvoiceModel:
    return InvoiceModel(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        vendor_id=invoice.vendor_id,
        po_id=invoice.po_id,
        status=invoice.status.value,
        line_items=[_line_item_to_dict(item) for item in invoice.line_items],
        document_reference=invoice.document_reference,
        match_discrepancies=invoice.match_discrepancies,
        created_at=invoice.created_at,
    )


def apply_domain_to_existing_model(invoice: Invoice, model: InvoiceModel) -> None:
    model.status = invoice.status.value
    model.document_reference = invoice.document_reference
    model.match_discrepancies = invoice.match_discrepancies
