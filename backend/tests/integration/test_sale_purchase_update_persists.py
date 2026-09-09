"""Real-Postgres regression test for a bug found during live verification:
Sale/Purchase's `apply_domain_to_existing_model` mappers only ever synced
amount_received_cents/status (written for record_payment/void, the only
two mutations that existed before editing was added) — UpdateSaleUseCase/
UpdatePurchaseUseCase correctly mutated the in-memory entity and returned
a response reflecting the edit, but the actual database row was never
touched for any of the newly-editable fields, so a follow-up read showed
the pre-edit data. A FakeUnitOfWork-based unit test can never catch this
class of bug, since the fake's update() just replaces the whole in-memory
object regardless of what the real mapper does — hence a real-DB test.
Requires Docker; skipped automatically otherwise (see
tests/conftest.py:docker_available).
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.purchases.application.commands.create_purchase import (
    CreatePurchaseCommand,
    CreatePurchaseLineItemInput,
    CreatePurchaseUseCase,
)
from app.purchases.application.commands.update_purchase import (
    UpdatePurchaseCommand,
    UpdatePurchaseLineItemInput,
    UpdatePurchaseUseCase,
)
from app.purchases.application.queries.get_purchase import GetPurchaseQuery, GetPurchaseUseCase
from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
from app.sales.application.commands.update_sale import (
    UpdateSaleCommand,
    UpdateSaleLineItemInput,
    UpdateSaleUseCase,
)
from app.sales.application.queries.get_sale import GetSaleQuery, GetSaleUseCase

pytestmark = pytest.mark.integration


async def test_updated_sale_fields_actually_persist(db_session: AsyncSession) -> None:
    uow = AppUnitOfWork(db_session)
    business_id = uuid.uuid4()
    sale = await CreateSaleUseCase(uow).execute(
        CreateSaleCommand(
            business_id=business_id,
            invoice_number="INV-001",
            invoice_date=date(2026, 1, 1),
            line_items=[
                CreateSaleLineItemInput(
                    line_number=1, description="Widget", quantity=Decimal("2"), unit_price=Decimal("50")
                )
            ],
        )
    )

    await UpdateSaleUseCase(uow).execute(
        UpdateSaleCommand(
            business_id=business_id,
            sale_id=sale.id,
            invoice_number="INV-001-EDITED",
            invoice_date=date(2026, 2, 1),
            line_items=[
                UpdateSaleLineItemInput(
                    line_number=1, description="Gadget", quantity=Decimal("3"), unit_price=Decimal("10")
                )
            ],
            notes="edited",
        )
    )

    refetched = await GetSaleUseCase(uow).execute(GetSaleQuery(business_id=business_id, sale_id=sale.id))
    assert refetched.invoice_number == "INV-001-EDITED"
    assert refetched.invoice_date == date(2026, 2, 1)
    assert refetched.notes == "edited"
    assert refetched.total_amount.amount == Decimal("30.00")
    assert refetched.line_items[0].description == "Gadget"


async def test_updated_purchase_fields_actually_persist(db_session: AsyncSession) -> None:
    uow = AppUnitOfWork(db_session)
    business_id = uuid.uuid4()
    purchase = await CreatePurchaseUseCase(uow).execute(
        CreatePurchaseCommand(
            business_id=business_id,
            purchase_number="PO-001",
            vendor_id=uuid.uuid4(),
            purchase_date=date(2026, 1, 1),
            line_items=[
                CreatePurchaseLineItemInput(
                    line_number=1, description="Raw materials", quantity=Decimal("10"), unit_cost=Decimal("5")
                )
            ],
        )
    )
    new_vendor_id = uuid.uuid4()

    await UpdatePurchaseUseCase(uow).execute(
        UpdatePurchaseCommand(
            business_id=business_id,
            purchase_id=purchase.id,
            purchase_number="PO-001-EDITED",
            vendor_id=new_vendor_id,
            purchase_date=date(2026, 2, 1),
            line_items=[
                UpdatePurchaseLineItemInput(
                    line_number=1, description="New materials", quantity=Decimal("4"), unit_cost=Decimal("2")
                )
            ],
            notes="edited",
        )
    )

    refetched = await GetPurchaseUseCase(uow).execute(
        GetPurchaseQuery(business_id=business_id, purchase_id=purchase.id)
    )
    assert refetched.purchase_number == "PO-001-EDITED"
    assert refetched.vendor_id == new_vendor_id
    assert refetched.purchase_date == date(2026, 2, 1)
    assert refetched.notes == "edited"
    assert refetched.total_amount.amount == Decimal("8.00")
    assert refetched.line_items[0].description == "New materials"
