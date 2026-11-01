import uuid

from app.vendors.application.ports import VendorsUnitOfWork
from app.vendors.domain.entities import Vendor

_MAX_NAME = 255
_SCAN_LIMIT = 10_000


def _clean(name: str) -> str:
    return " ".join(name.split())[:_MAX_NAME]


async def ensure_supplier(uow: VendorsUnitOfWork, *, business_id: uuid.UUID, name: str) -> Vendor:
    """The business's vendor with this name (ignoring capitals and extra spaces), creating a name-only one
    if there is none, so every supplier named on a purchase appears on the Vendors page. The caller
    commits, in the same transaction as the purchase.
    """
    cleaned = _clean(name)
    wanted = cleaned.lower()
    existing, _ = await uow.vendors.list_for_business(business_id, offset=0, limit=_SCAN_LIMIT)
    for vendor in existing:
        if _clean(vendor.legal_name).lower() == wanted:
            return vendor
    vendor = Vendor.create_supplier(legal_name=cleaned, business_id=business_id)
    uow.vendors.add(vendor)
    return vendor
