"""The udhaar list (who owes what) and the next invoice number in a business's own series."""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
from app.sales.application.commands.record_payment import RecordSalePaymentCommand, RecordSalePaymentUseCase
from app.sales.application.commands.void_sale import VoidSaleCommand, VoidSaleUseCase
from app.sales.application.queries.get_receivables import GetReceivablesQuery, GetReceivablesUseCase
from app.sales.application.queries.next_invoice_number import NextInvoiceNumberQuery, NextInvoiceNumberUseCase
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

BUSINESS = uuid.uuid4()
TODAY = date(2026, 11, 24)


async def _sale(
    uow: FakeUnitOfWork,
    number: str,
    price: str,
    *,
    customer: uuid.UUID | None = None,
    due: date | None = None,
    on: date = date(2026, 11, 1),
):
    sale = await CreateSaleUseCase(uow).execute(
        CreateSaleCommand(
            business_id=BUSINESS,
            invoice_number=number,
            invoice_date=on,
            due_date=due,
            customer_id=customer,
            line_items=[
                CreateSaleLineItemInput(
                    line_number=1, description="Goods", quantity=Decimal("1"), unit_price=Decimal(price)
                )
            ],
        )
    )
    # the fake keeps insertion order, so spread created_at to make "newest" unambiguous
    sale.created_at = datetime(2026, 11, 1, tzinfo=timezone.utc) + timedelta(minutes=len(uow.sales._store))
    return sale


async def _receivables(uow: FakeUnitOfWork):
    return await GetReceivablesUseCase(uow).execute(GetReceivablesQuery(business_id=BUSINESS, today=TODAY))


async def test_who_owes_what_is_grouped_by_customer_largest_first() -> None:
    uow = FakeUnitOfWork()
    asha, ravi = uuid.uuid4(), uuid.uuid4()
    await _sale(uow, "INV-1", "300", customer=ravi)
    await _sale(uow, "INV-2", "500", customer=asha)
    await _sale(uow, "INV-3", "250", customer=asha)

    groups = await _receivables(uow)

    assert [(g.customer_id, g.outstanding) for g in groups] == [
        (asha, Decimal("750.00")),
        (ravi, Decimal("300.00")),
    ]
    assert [i.invoice_number for i in groups[0].invoices] == ["INV-2", "INV-3"]


async def test_paid_and_void_sales_do_not_count_and_part_payments_reduce_the_balance() -> None:
    uow = FakeUnitOfWork()
    asha = uuid.uuid4()
    paid = await _sale(uow, "INV-1", "100", customer=asha)
    await RecordSalePaymentUseCase(uow).execute(
        RecordSalePaymentCommand(business_id=BUSINESS, sale_id=paid.id, amount=Decimal("100"))
    )
    part = await _sale(uow, "INV-2", "400", customer=asha)
    await RecordSalePaymentUseCase(uow).execute(
        RecordSalePaymentCommand(business_id=BUSINESS, sale_id=part.id, amount=Decimal("150"))
    )
    voided = await _sale(uow, "INV-3", "999", customer=asha)
    await VoidSaleUseCase(uow).execute(VoidSaleCommand(business_id=BUSINESS, sale_id=voided.id))

    (group,) = await _receivables(uow)

    assert group.outstanding == Decimal("250.00")
    assert [i.invoice_number for i in group.invoices] == ["INV-2"]


async def test_a_sale_with_no_customer_is_its_own_group() -> None:
    uow = FakeUnitOfWork()
    await _sale(uow, "INV-1", "80")

    (group,) = await _receivables(uow)

    assert group.customer_id is None and group.outstanding == Decimal("80.00")


async def test_days_overdue_counts_from_the_due_date() -> None:
    uow = FakeUnitOfWork()
    asha = uuid.uuid4()
    await _sale(uow, "INV-1", "100", customer=asha, due=TODAY - timedelta(days=12))
    await _sale(uow, "INV-2", "100", customer=asha, due=TODAY + timedelta(days=5))
    await _sale(uow, "INV-3", "100", customer=asha)

    (group,) = await _receivables(uow)

    by_number = {i.invoice_number: i.days_overdue for i in group.invoices}
    assert by_number == {"INV-1": 12, "INV-2": 0, "INV-3": 0}
    assert group.days_overdue == 12


async def _next(uow: FakeUnitOfWork) -> str:
    return await NextInvoiceNumberUseCase(uow).execute(NextInvoiceNumberQuery(business_id=BUSINESS))


async def test_the_first_invoice_number_is_inv_0001() -> None:
    assert await _next(FakeUnitOfWork()) == "INV-0001"


async def test_the_next_number_continues_the_series_with_the_same_prefix_and_width() -> None:
    uow = FakeUnitOfWork()
    await _sale(uow, "SH/26-27/0009", "10")
    assert await _next(uow) == "SH/26-27/0010"

    await _sale(uow, "SH/26-27/0010", "10")
    assert await _next(uow) == "SH/26-27/0011"


async def test_a_number_already_in_use_is_skipped() -> None:
    uow = FakeUnitOfWork()
    await _sale(uow, "INV-0005", "10")
    await _sale(uow, "INV-0006", "10")
    # entered out of order: the newest sale is -0003, but -0004 .. -0006 are taken or about to be
    await _sale(uow, "INV-0004", "10")
    await _sale(uow, "INV-0003", "10")

    assert await _next(uow) == "INV-0007"


async def test_a_series_without_a_trailing_number_falls_back_to_the_default() -> None:
    uow = FakeUnitOfWork()
    await _sale(uow, "FIRST-SALE", "10")

    assert await _next(uow) == "INV-0001"
