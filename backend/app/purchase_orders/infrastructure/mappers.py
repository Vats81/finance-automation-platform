from decimal import Decimal

from app.purchase_orders.domain.entities import PurchaseOrder
from app.purchase_orders.domain.value_objects import PurchaseOrderLineItem, PurchaseOrderStatus
from app.purchase_orders.infrastructure.models import PurchaseOrderModel
from app.shared.domain.value_objects import Money


def _line_item_to_dict(item: PurchaseOrderLineItem) -> dict:
    return {
        "line_number": item.line_number,
        "description": item.description,
        "quantity": str(item.quantity),
        "unit_price_cents": item.unit_price.cents,
    }


def _dict_to_line_item(data: dict) -> PurchaseOrderLineItem:
    return PurchaseOrderLineItem(
        line_number=data["line_number"],
        description=data["description"],
        quantity=Decimal(data["quantity"]),
        unit_price=Money.from_cents(data["unit_price_cents"]),
    )


def model_to_domain(model: PurchaseOrderModel) -> PurchaseOrder:
    return PurchaseOrder(
        entity_id=model.id,
        po_number=model.po_number,
        vendor_id=model.vendor_id,
        line_items=[_dict_to_line_item(item) for item in model.line_items],
        status=PurchaseOrderStatus(model.status),
        created_at=model.created_at,
    )


def domain_to_model(po: PurchaseOrder) -> PurchaseOrderModel:
    return PurchaseOrderModel(
        id=po.id,
        po_number=po.po_number,
        vendor_id=po.vendor_id,
        status=po.status.value,
        line_items=[_line_item_to_dict(item) for item in po.line_items],
        created_at=po.created_at,
    )


def apply_domain_to_existing_model(po: PurchaseOrder, model: PurchaseOrderModel) -> None:
    model.status = po.status.value
