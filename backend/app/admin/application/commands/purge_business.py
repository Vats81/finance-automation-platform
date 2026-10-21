import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.domain.exceptions import BusinessNotFoundException
from app.business.infrastructure.models import BusinessMembershipModel, BusinessModel
from app.customers.infrastructure.models import CustomerModel
from app.expenses.infrastructure.models import ExpenseModel
from app.inventory.infrastructure.models import ProductModel
from app.purchases.infrastructure.models import PurchaseModel
from app.sales.infrastructure.models import SaleModel
from app.shared.domain.exceptions import ValidationException
from app.vendors.infrastructure.models import VendorModel

logger = logging.getLogger(__name__)

# Every table keyed by business_id. tests/unit/admin/test_purge_business.py
# fails if a new business-scoped table is added without being listed here, so
# a purge can't silently leave a business's data behind.
BUSINESS_SCOPED_MODELS: tuple[type, ...] = (
    SaleModel,
    PurchaseModel,
    ExpenseModel,
    ProductModel,
    CustomerModel,
    VendorModel,
    BusinessMembershipModel,
)


@dataclass(frozen=True)
class PurgeBusinessCommand:
    business_id: uuid.UUID
    confirm_name: str
    actor_user_id: uuid.UUID


class PurgeBusinessUseCase:
    """Permanently deletes a business and every row scoped to it. Irreversible,
    so the caller must retype the business's exact name. Takes the raw session
    (like ExportBackupUseCase) because it is a bulk operation across contexts,
    not an aggregate operation. Users are never touched here; see
    DeleteUserUseCase.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, command: PurgeBusinessCommand) -> None:
        business = await self._session.get(BusinessModel, command.business_id)
        if business is None:
            raise BusinessNotFoundException(f"Business {command.business_id} not found")
        if command.confirm_name.strip() != business.name:
            raise ValidationException("Confirmation does not match the business name; nothing was deleted.")

        for model in BUSINESS_SCOPED_MODELS:
            await self._session.execute(
                delete(model).where(model.business_id == command.business_id)  # type: ignore[attr-defined]
            )
        await self._session.delete(business)
        await self._session.commit()
        logger.warning(
            "Platform admin %s purged business %s (%s) and all of its data",
            command.actor_user_id,
            command.business_id,
            business.name,
        )
