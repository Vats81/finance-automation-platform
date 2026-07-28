import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
from app.sales.application.commands.record_payment import RecordSalePaymentCommand, RecordSalePaymentUseCase
from app.sales.application.commands.void_sale import VoidSaleCommand, VoidSaleUseCase
from app.sales.application.queries.get_sale import GetSaleQuery, GetSaleUseCase
from app.sales.application.queries.list_sales import ListSalesQuery, ListSalesUseCase
from app.sales.domain.exceptions import SaleNotFoundException
from app.sales.domain.value_objects import SalePaymentStatus
from app.shared.application.pagination import PageRequest
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


def make_create_command(business_id: uuid.UUID, **overrides) -> CreateSaleCommand:
    defaults = dict(
        business_id=business_id,
        invoice_number="INV-001",
        invoice_date=date(2026, 1, 1),
        line_items=[
            CreateSaleLineItemInput(
                line_number=1, description="Widget", quantity=Decimal("2"), unit_price=Decimal("50")
            )
        ],
    )
    defaults.update(overrides)
    return CreateSaleCommand(**defaults)


async def test_create_and_get_sale() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    created = await CreateSaleUseCase(uow).execute(make_create_command(business_id))

    fetched = await GetSaleUseCase(uow).execute(GetSaleQuery(business_id=business_id, sale_id=created.id))
    assert fetched.invoice_number == "INV-001"
    assert fetched.total_amount.amount == Decimal("100.00")


async def test_get_sale_from_wrong_business_raises() -> None:
    uow = FakeUnitOfWork()
    sale = await CreateSaleUseCase(uow).execute(make_create_command(uuid.uuid4()))

    with pytest.raises(SaleNotFoundException):
        await GetSaleUseCase(uow).execute(GetSaleQuery(business_id=uuid.uuid4(), sale_id=sale.id))


async def test_list_sales_is_scoped_per_business() -> None:
    uow = FakeUnitOfWork()
    business_a = uuid.uuid4()
    business_b = uuid.uuid4()
    await CreateSaleUseCase(uow).execute(make_create_command(business_a, invoice_number="A-1"))
    await CreateSaleUseCase(uow).execute(make_create_command(business_b, invoice_number="B-1"))

    page = await ListSalesUseCase(uow).execute(ListSalesQuery(business_id=business_a, page=PageRequest()))

    assert page.total == 1
    assert page.items[0].invoice_number == "A-1"


async def test_record_payment_use_case_updates_payment_status() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    sale = await CreateSaleUseCase(uow).execute(make_create_command(business_id))

    updated = await RecordSalePaymentUseCase(uow).execute(
        RecordSalePaymentCommand(business_id=business_id, sale_id=sale.id, amount=Decimal("100"))
    )

    assert updated.payment_status == SalePaymentStatus.PAID


async def test_void_sale_use_case() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    sale = await CreateSaleUseCase(uow).execute(make_create_command(business_id))

    voided = await VoidSaleUseCase(uow).execute(VoidSaleCommand(business_id=business_id, sale_id=sale.id))

    assert voided.status.value == "void"
