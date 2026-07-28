from decimal import Decimal

from app.sales.domain.entities import Sale
from app.sales.domain.value_objects import SaleLineItem, SaleStatus
from app.sales.infrastructure.models import SaleModel
from app.shared.domain.value_objects import Money


def _line_item_to_dict(item: SaleLineItem) -> dict:
    return {
        "line_number": item.line_number,
        "description": item.description,
        "quantity": str(item.quantity),
        "unit_price_cents": item.unit_price.cents,
    }


def _dict_to_line_item(data: dict) -> SaleLineItem:
    return SaleLineItem(
        line_number=data["line_number"],
        description=data["description"],
        quantity=Decimal(data["quantity"]),
        unit_price=Money.from_cents(data["unit_price_cents"]),
    )


def model_to_domain(model: SaleModel) -> Sale:
    return Sale(
        entity_id=model.id,
        business_id=model.business_id,
        invoice_number=model.invoice_number,
        customer_id=model.customer_id,
        invoice_date=model.invoice_date,
        due_date=model.due_date,
        line_items=[_dict_to_line_item(item) for item in model.line_items],
        discount=Money.from_cents(model.discount_cents),
        tax=Money.from_cents(model.tax_cents),
        amount_received=Money.from_cents(model.amount_received_cents),
        notes=model.notes,
        status=SaleStatus(model.status),
        created_at=model.created_at,
    )


def domain_to_model(sale: Sale) -> SaleModel:
    return SaleModel(
        id=sale.id,
        business_id=sale.business_id,
        invoice_number=sale.invoice_number,
        customer_id=sale.customer_id,
        invoice_date=sale.invoice_date,
        due_date=sale.due_date,
        line_items=[_line_item_to_dict(item) for item in sale.line_items],
        discount_cents=sale.discount.cents,
        tax_cents=sale.tax.cents,
        amount_received_cents=sale.amount_received.cents,
        notes=sale.notes,
        status=sale.status.value,
        created_at=sale.created_at,
    )


def apply_domain_to_existing_model(sale: Sale, model: SaleModel) -> None:
    model.amount_received_cents = sale.amount_received.cents
    model.status = sale.status.value
