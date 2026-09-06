import datetime
import decimal
import uuid
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.infrastructure.models import BusinessMembershipModel, BusinessModel
from app.customers.infrastructure.models import CustomerModel
from app.expenses.infrastructure.models import ExpenseModel
from app.identity.infrastructure.models import UserModel
from app.inventory.infrastructure.models import ProductModel
from app.purchases.infrastructure.models import PurchaseModel
from app.sales.infrastructure.models import SaleModel
from app.vendors.infrastructure.models import VendorModel

# Scoped to the SMB product's own tables — the dormant AP-automation
# contexts (invoices, purchase_orders, approvals, payments, audit log)
# have no real usage on this deployment and would just add noise to a
# backup meant for disaster recovery of actual business data.
_TABLES: dict[str, type] = {
    "users": UserModel,
    "businesses": BusinessModel,
    "business_memberships": BusinessMembershipModel,
    "customers": CustomerModel,
    "vendors": VendorModel,
    "products": ProductModel,
    "sales": SaleModel,
    "purchases": PurchaseModel,
    "expenses": ExpenseModel,
}


def _json_safe(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime.datetime | datetime.date):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    return value


def _row_to_dict(instance: Any) -> dict[str, Any]:
    mapper = inspect(instance).mapper
    return {column.key: _json_safe(getattr(instance, column.key)) for column in mapper.columns}


class ExportBackupUseCase:
    """A logical (not byte-for-byte SQL) backup: every row of every SMB
    table, serialized to JSON. Deliberately Python-only — no `pg_dump`
    binary is installed in the deployed image (would need adding
    `postgresql-client` to the Dockerfile for a real SQL dump), and this
    is restorable well enough by reading the JSON back in, matching this
    codebase's established preference for pure-Python tooling over new
    system dependencies (see the CSV import module's own reasoning).
    Admin-only (see api/routes.py's router-level require_platform_admin).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self) -> dict[str, list[dict[str, Any]]]:
        backup: dict[str, list[dict[str, Any]]] = {}
        for table_name, model in _TABLES.items():
            result: Any = await self._session.execute(select(model))
            backup[table_name] = [_row_to_dict(row) for row in result.scalars().all()]
        return backup
