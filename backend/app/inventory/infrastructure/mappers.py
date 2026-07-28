from app.inventory.domain.entities import Product
from app.inventory.domain.value_objects import ProductStatus
from app.inventory.infrastructure.models import ProductModel
from app.shared.domain.value_objects import Money


def model_to_domain(model: ProductModel) -> Product:
    return Product(
        entity_id=model.id,
        business_id=model.business_id,
        name=model.name,
        sku=model.sku,
        category=model.category,
        selling_price=Money.from_cents(model.selling_price_cents),
        purchase_cost=Money.from_cents(model.purchase_cost_cents),
        current_quantity=model.current_quantity,
        minimum_stock_level=model.minimum_stock_level,
        reorder_quantity=model.reorder_quantity,
        unit_of_measurement=model.unit_of_measurement,
        vendor_id=model.vendor_id,
        status=ProductStatus(model.status),
        created_at=model.created_at,
    )


def domain_to_model(product: Product) -> ProductModel:
    return ProductModel(
        id=product.id,
        business_id=product.business_id,
        name=product.name,
        sku=product.sku,
        category=product.category,
        selling_price_cents=product.selling_price.cents,
        purchase_cost_cents=product.purchase_cost.cents,
        current_quantity=product.current_quantity,
        minimum_stock_level=product.minimum_stock_level,
        reorder_quantity=product.reorder_quantity,
        unit_of_measurement=product.unit_of_measurement,
        vendor_id=product.vendor_id,
        status=product.status.value,
        created_at=product.created_at,
    )


def apply_domain_to_existing_model(product: Product, model: ProductModel) -> None:
    model.name = product.name
    model.category = product.category
    model.selling_price_cents = product.selling_price.cents
    model.purchase_cost_cents = product.purchase_cost.cents
    model.current_quantity = product.current_quantity
    model.minimum_stock_level = product.minimum_stock_level
    model.reorder_quantity = product.reorder_quantity
    model.status = product.status.value
