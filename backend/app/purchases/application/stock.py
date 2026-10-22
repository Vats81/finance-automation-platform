"""Linking purchase lines to products, and moving stock for them.

Kept in one place so create, edit and void agree on the rules:
* a line may link to a product only if the product belongs to the same business;
* with add_to_stock, each linked line adds its quantity to that product's stock
  in the same transaction as the purchase (so both happen or neither does);
* a purchase that added stock is flagged, and voiding it takes the stock back
  out - refusing, with nothing changed, if some of it has already been used.
"""

import uuid
from decimal import Decimal

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.inventory.domain.exceptions import NegativeStockException, ProductNotFoundException
from app.purchases.domain.entities import Purchase
from app.purchases.domain.exceptions import StockAlreadyUsedException
from app.purchases.domain.value_objects import PurchaseLineItem
from app.shared.domain.exceptions import ValidationException

_STOCK_PLACES = Decimal("0.0001")


async def ensure_products_belong_to_business(
    uow: AppUnitOfWork, business_id: uuid.UUID, line_items: list[PurchaseLineItem]
) -> None:
    """A product_id from another business must never be accepted, even as a
    plain link: it would otherwise let one tenant reference another's records.
    """
    for product_id in {i.product_id for i in line_items if i.product_id is not None}:
        if await uow.products.get_by_id_for_business(product_id, business_id) is None:
            raise ProductNotFoundException(f"Product {product_id} not found")


async def link_and_add_stock(
    uow: AppUnitOfWork,
    *,
    business_id: uuid.UUID,
    purchase_number: str,
    line_items: list[PurchaseLineItem],
    add_to_stock: bool,
) -> bool:
    """Validates product links and, if asked, adds the stock. Returns whether
    any stock was actually added.
    """
    await ensure_products_belong_to_business(uow, business_id, line_items)
    if not add_to_stock:
        return False

    linked = [item for item in line_items if item.product_id is not None]
    for item in linked:
        if item.quantity != item.quantity.quantize(_STOCK_PLACES):
            raise ValidationException(
                f"Stock can be tracked to 4 decimal places; the count for '{item.description}' has more."
            )
    for item in linked:
        assert item.product_id is not None
        product = await uow.products.get_by_id_for_business(item.product_id, business_id)
        assert product is not None  # verified above
        product.adjust_stock(delta=item.quantity, reason=f"Purchase {purchase_number}")
        await uow.products.update(product)
    return bool(linked)


async def remove_added_stock(uow: AppUnitOfWork, purchase: Purchase) -> None:
    """Takes back the stock a purchase added. All-or-nothing: if any product no
    longer has enough, nothing is changed and the user is told which one.
    """
    for item in purchase.line_items:
        if item.product_id is None:
            continue
        product = await uow.products.get_by_id_for_business(item.product_id, purchase.business_id)
        if product is None:
            continue  # the product was deleted; there is no stock left to take back
        try:
            product.adjust_stock(delta=-item.quantity, reason=f"Purchase {purchase.purchase_number} voided")
        except NegativeStockException as exc:
            raise StockAlreadyUsedException(
                f"Can't void: '{product.name}' has only {product.current_quantity} left in stock but this "
                f"purchase added {item.quantity}. Adjust the stock first, then void."
            ) from exc
        await uow.products.update(product)
