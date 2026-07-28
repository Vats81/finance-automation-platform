import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.vendors.domain.entities import Vendor
from app.vendors.domain.exceptions import VendorNotFoundException
from app.vendors.domain.repository import IVendorRepository
from app.vendors.infrastructure.mappers import (
    apply_domain_to_existing_model,
    domain_to_model,
    model_to_domain,
)
from app.vendors.infrastructure.models import VendorModel


class SqlAlchemyVendorRepository(IVendorRepository):
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> AsyncSession:
        return self._uow.session

    async def get_by_id(self, vendor_id: uuid.UUID) -> Vendor | None:
        model = await self._session.get(VendorModel, vendor_id)
        return model_to_domain(model) if model else None

    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[Vendor], int]:
        total = (await self._session.execute(select(func.count()).select_from(VendorModel))).scalar_one()
        stmt = select(VendorModel).order_by(VendorModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        vendors = [model_to_domain(m) for m in result.scalars().all()]
        return vendors, total

    async def get_by_id_for_business(self, vendor_id: uuid.UUID, business_id: uuid.UUID) -> Vendor | None:
        stmt = select(VendorModel).where(
            VendorModel.id == vendor_id, VendorModel.business_id == business_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model_to_domain(model) if model else None

    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Vendor], int]:
        total = (
            await self._session.execute(
                select(func.count()).select_from(VendorModel).where(VendorModel.business_id == business_id)
            )
        ).scalar_one()
        stmt = (
            select(VendorModel)
            .where(VendorModel.business_id == business_id)
            .order_by(VendorModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        vendors = [model_to_domain(m) for m in result.scalars().all()]
        return vendors, total

    def add(self, vendor: Vendor) -> None:
        self._session.add(domain_to_model(vendor))
        self._uow.collect_events(vendor)

    async def update(self, vendor: Vendor) -> None:
        model = await self._session.get(VendorModel, vendor.id)
        if model is None:
            raise VendorNotFoundException(f"Vendor {vendor.id} not found")
        apply_domain_to_existing_model(vendor, model)
        self._uow.collect_events(vendor)
