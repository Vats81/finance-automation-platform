import uuid
from decimal import Decimal

from app.purchases.domain.entities import Purchase
from app.purchases.domain.value_objects import PurchaseLineItem, PurchaseStatus
from app.purchases.infrastructure.models import PurchaseModel
from app.shared.domain.value_objects import Money


def _line_item_to_dict(item: PurchaseLineItem) -> dict:
    return {
        "line_number": item.line_number,
        "description": item.description,
        "quantity": str(item.quantity),
        "unit_cost_cents": item.unit_cost.cents,
        "product_id": str(item.product_id) if item.product_id else None,
    }


def _dict_to_line_item(data: dict) -> PurchaseLineItem:
    return PurchaseLineItem(
        line_number=data["line_number"],
        description=data["description"],
        quantity=Decimal(data["quantity"]),
        unit_cost=Money.from_cents(data["unit_cost_cents"]),
        product_id=uuid.UUID(data["product_id"]) if data.get("product_id") else None,
    )


def model_to_domain(model: PurchaseModel) -> Purchase:
    return Purchase(
        entity_id=model.id,
        business_id=model.business_id,
        purchase_number=model.purchase_number,
        vendor_id=model.vendor_id,
        purchase_date=model.purchase_date,
        due_date=model.due_date,
        line_items=[_dict_to_line_item(item) for item in model.line_items],
        tax=Money.from_cents(model.tax_cents),
        amount_paid=Money.from_cents(model.amount_paid_cents),
        notes=model.notes,
        status=PurchaseStatus(model.status),
        created_at=model.created_at,
    )


def domain_to_model(purchase: Purchase) -> PurchaseModel:
    return PurchaseModel(
        id=purchase.id,
        business_id=purchase.business_id,
        purchase_number=purchase.purchase_number,
        vendor_id=purchase.vendor_id,
        purchase_date=purchase.purchase_date,
        due_date=purchase.due_date,
        line_items=[_line_item_to_dict(item) for item in purchase.line_items],
        tax_cents=purchase.tax.cents,
        amount_paid_cents=purchase.amount_paid.cents,
        notes=purchase.notes,
        status=purchase.status.value,
        created_at=purchase.created_at,
    )


def apply_domain_to_existing_model(purchase: Purchase, model: PurchaseModel) -> None:
    model.purchase_number = purchase.purchase_number
    model.vendor_id = purchase.vendor_id
    model.purchase_date = purchase.purchase_date
    model.due_date = purchase.due_date
    model.line_items = [_line_item_to_dict(item) for item in purchase.line_items]
    model.tax_cents = purchase.tax.cents
    model.amount_paid_cents = purchase.amount_paid.cents
    model.notes = purchase.notes
    model.status = purchase.status.value
