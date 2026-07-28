import uuid
from datetime import date
from decimal import Decimal

from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
from app.sales.application.commands.record_payment import RecordSalePaymentCommand, RecordSalePaymentUseCase
from app.sales.application.commands.void_sale import VoidSaleCommand, VoidSaleUseCase
from app.sales.application.queries.list_outstanding_sales import (
    ListOutstandingSalesQuery,
    ListOutstandingSalesUseCase,
)
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


def make_create_command(business_id: uuid.UUID, **overrides) -> CreateSaleCommand:
    defaults = dict(
        business_id=business_id,
        invoice_number="INV-001",
        invoice_date=date(2026, 1, 1),
        line_items=[
            CreateSaleLineItemInput(
                line_number=1, description="Widget", quantity=Decimal("1"), unit_price=Decimal("100")
            )
        ],
    )
    defaults.update(overrides)
    return CreateSaleCommand(**defaults)


async def test_outstanding_excludes_paid_and_void_but_includes_unpaid_and_partial() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    unpaid = await CreateSaleUseCase(uow).execute(make_create_command(business_id, invoice_number="UNPAID"))
    partial = await CreateSaleUseCase(uow).execute(make_create_command(business_id, invoice_number="PARTIAL"))
    await RecordSalePaymentUseCase(uow).execute(
        RecordSalePaymentCommand(business_id=business_id, sale_id=partial.id, amount=Decimal("40"))
    )
    paid = await CreateSaleUseCase(uow).execute(make_create_command(business_id, invoice_number="PAID"))
    await RecordSalePaymentUseCase(uow).execute(
        RecordSalePaymentCommand(business_id=business_id, sale_id=paid.id, amount=Decimal("100"))
    )
    voided = await CreateSaleUseCase(uow).execute(make_create_command(business_id, invoice_number="VOIDED"))
    await VoidSaleUseCase(uow).execute(VoidSaleCommand(business_id=business_id, sale_id=voided.id))

    outstanding = await ListOutstandingSalesUseCase(uow).execute(
        ListOutstandingSalesQuery(business_id=business_id)
    )

    invoice_numbers = {sale.invoice_number for sale in outstanding}
    assert invoice_numbers == {"UNPAID", "PARTIAL"}
    assert unpaid.id in {s.id for s in outstanding}


async def test_outstanding_is_scoped_per_business() -> None:
    uow = FakeUnitOfWork()
    business_a = uuid.uuid4()
    business_b = uuid.uuid4()
    await CreateSaleUseCase(uow).execute(make_create_command(business_a, invoice_number="A-1"))
    await CreateSaleUseCase(uow).execute(make_create_command(business_b, invoice_number="B-1"))

    outstanding = await ListOutstandingSalesUseCase(uow).execute(
        ListOutstandingSalesQuery(business_id=business_a)
    )

    assert [s.invoice_number for s in outstanding] == ["A-1"]


async def test_outstanding_sorts_by_due_date_with_nulls_last() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    await CreateSaleUseCase(uow).execute(
        make_create_command(business_id, invoice_number="NO-DUE-DATE", due_date=None)
    )
    await CreateSaleUseCase(uow).execute(
        make_create_command(business_id, invoice_number="LATER", due_date=date(2026, 6, 1))
    )
    await CreateSaleUseCase(uow).execute(
        make_create_command(business_id, invoice_number="SOONER", due_date=date(2026, 2, 1))
    )

    outstanding = await ListOutstandingSalesUseCase(uow).execute(
        ListOutstandingSalesQuery(business_id=business_id)
    )

    assert [s.invoice_number for s in outstanding] == ["SOONER", "LATER", "NO-DUE-DATE"]
