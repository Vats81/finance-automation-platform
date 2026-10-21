import uuid
from datetime import date
from decimal import Decimal

import pytest

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
from app.sales.application.commands.void_sale import VoidSaleCommand, VoidSaleUseCase
from app.sales.domain.exceptions import DuplicateInvoiceNumberException
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


def _create(business_id: uuid.UUID, number: str) -> CreateSaleCommand:
    return CreateSaleCommand(
        business_id=business_id,
        invoice_number=number,
        invoice_date=date(2026, 10, 1),
        line_items=[CreateSaleLineItemInput(1, "x", Decimal("1"), Decimal("10"))],
    )


async def test_the_same_invoice_number_cannot_be_used_twice_in_a_business() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    await CreateSaleUseCase(uow).execute(_create(business_id, "INV-1"))

    with pytest.raises(DuplicateInvoiceNumberException):
        await CreateSaleUseCase(uow).execute(_create(business_id, "INV-1"))


async def test_other_businesses_can_use_the_same_number() -> None:
    uow = FakeUnitOfWork()
    await CreateSaleUseCase(uow).execute(_create(uuid.uuid4(), "INV-1"))

    await CreateSaleUseCase(uow).execute(_create(uuid.uuid4(), "INV-1"))


async def test_a_voided_invoices_number_can_be_reissued() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    first = await CreateSaleUseCase(uow).execute(_create(business_id, "INV-1"))
    await VoidSaleUseCase(uow).execute(VoidSaleCommand(business_id=business_id, sale_id=first.id))

    await CreateSaleUseCase(uow).execute(_create(business_id, "INV-1"))


async def test_renaming_a_sale_to_an_existing_number_is_rejected_but_keeping_its_own_is_fine() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    await CreateSaleUseCase(uow).execute(_create(business_id, "INV-1"))
    second = await CreateSaleUseCase(uow).execute(_create(business_id, "INV-2"))

    def update(number: str) -> UpdateSaleCommand:
        return UpdateSaleCommand(
            business_id=business_id,
            sale_id=second.id,
            invoice_number=number,
            invoice_date=date(2026, 10, 1),
            line_items=[UpdateSaleLineItemInput(1, "x", Decimal("1"), Decimal("10"))],
        )

    await UpdateSaleUseCase(uow).execute(update("INV-2"))
    with pytest.raises(DuplicateInvoiceNumberException):
        await UpdateSaleUseCase(uow).execute(update("INV-1"))
