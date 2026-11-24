"""Real-Postgres test of the invoice share link storage: the token is found by its hash, and revoking works.
Requires Docker; skipped automatically otherwise (see tests/conftest.py:docker_available).
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
from app.sales.application.commands.share_invoice import (
    CreateInvoiceShareLinkCommand,
    CreateInvoiceShareLinkUseCase,
    ResolveInvoiceShareLinkUseCase,
    RevokeInvoiceShareLinksCommand,
    RevokeInvoiceShareLinksUseCase,
)
from app.sales.domain.exceptions import InvoiceLinkNotFoundException

pytestmark = pytest.mark.integration


async def test_a_link_opens_its_invoice_until_revoked(db_session: AsyncSession) -> None:
    uow = AppUnitOfWork(db_session)
    business_id = uuid.uuid4()
    sale = await CreateSaleUseCase(uow).execute(
        CreateSaleCommand(
            business_id=business_id,
            invoice_number="INV-LINK",
            invoice_date=date(2026, 11, 1),
            line_items=[
                CreateSaleLineItemInput(
                    line_number=1, description="Widget", quantity=Decimal("1"), unit_price=Decimal("10")
                )
            ],
        )
    )

    link, token = await CreateInvoiceShareLinkUseCase(uow).execute(
        CreateInvoiceShareLinkCommand(business_id=business_id, sale_id=sale.id)
    )

    assert link.expires_at > datetime.now(timezone.utc)
    opened = await ResolveInvoiceShareLinkUseCase(uow).execute(token)
    assert opened.id == sale.id

    revoked = await RevokeInvoiceShareLinksUseCase(uow).execute(
        RevokeInvoiceShareLinksCommand(business_id=business_id, sale_id=sale.id)
    )
    assert revoked == 1
    with pytest.raises(InvoiceLinkNotFoundException):
        await ResolveInvoiceShareLinkUseCase(uow).execute(token)
