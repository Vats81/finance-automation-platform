import uuid
from datetime import date
from decimal import Decimal

from app.dashboard.application.queries.get_dashboard_summary import (
    GetDashboardSummaryQuery,
    GetDashboardSummaryUseCase,
)
from app.expenses.application.commands.create_expense import CreateExpenseCommand, CreateExpenseUseCase
from app.expenses.domain.value_objects import PaymentMethod
from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
from app.sales.application.commands.record_payment import RecordSalePaymentCommand, RecordSalePaymentUseCase
from app.sales.application.commands.void_sale import VoidSaleCommand, VoidSaleUseCase
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


def make_sale_command(business_id: uuid.UUID, **overrides) -> CreateSaleCommand:
    defaults = dict(
        business_id=business_id,
        invoice_number="INV-001",
        invoice_date=date(2026, 1, 15),
        line_items=[
            CreateSaleLineItemInput(
                line_number=1, description="Widget", quantity=Decimal("1"), unit_price=Decimal("100")
            )
        ],
    )
    defaults.update(overrides)
    return CreateSaleCommand(**defaults)


def make_expense_command(business_id: uuid.UUID, **overrides) -> CreateExpenseCommand:
    defaults = dict(
        business_id=business_id,
        expense_date=date(2026, 1, 15),
        category="Rent",
        description="Office rent",
        amount=Decimal("30"),
        payment_method=PaymentMethod.BANK_TRANSFER,
    )
    defaults.update(overrides)
    return CreateExpenseCommand(**defaults)


async def test_empty_business_returns_all_zeros() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    summary = await GetDashboardSummaryUseCase(uow).execute(
        GetDashboardSummaryQuery(business_id=business_id)
    )

    assert summary.total_revenue == Decimal("0")
    assert summary.total_expenses == Decimal("0")
    assert summary.net_profit == Decimal("0")
    assert summary.outstanding_receivables == Decimal("0")


async def test_computes_revenue_expenses_and_net_profit() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    await CreateSaleUseCase(uow).execute(make_sale_command(business_id))
    await CreateExpenseUseCase(uow).execute(make_expense_command(business_id))

    summary = await GetDashboardSummaryUseCase(uow).execute(
        GetDashboardSummaryQuery(business_id=business_id)
    )

    assert summary.total_revenue == Decimal("100.00")
    assert summary.total_expenses == Decimal("30.00")
    assert summary.net_profit == Decimal("70.00")


async def test_records_outside_date_range_are_excluded() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    await CreateSaleUseCase(uow).execute(
        make_sale_command(business_id, invoice_date=date(2025, 6, 1))
    )
    await CreateExpenseUseCase(uow).execute(
        make_expense_command(business_id, expense_date=date(2025, 6, 1))
    )

    summary = await GetDashboardSummaryUseCase(uow).execute(
        GetDashboardSummaryQuery(
            business_id=business_id, start_date=date(2026, 1, 1), end_date=date(2026, 1, 31)
        )
    )

    assert summary.total_revenue == Decimal("0")
    assert summary.total_expenses == Decimal("0")


async def test_voided_sales_and_expenses_are_excluded() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    sale = await CreateSaleUseCase(uow).execute(make_sale_command(business_id))
    await VoidSaleUseCase(uow).execute(VoidSaleCommand(business_id=business_id, sale_id=sale.id))

    summary = await GetDashboardSummaryUseCase(uow).execute(
        GetDashboardSummaryQuery(business_id=business_id)
    )

    assert summary.total_revenue == Decimal("0")
    assert summary.outstanding_receivables == Decimal("0")


async def test_outstanding_receivables_is_not_period_scoped() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    await CreateSaleUseCase(uow).execute(
        make_sale_command(business_id, invoice_date=date(2025, 1, 1))
    )

    summary = await GetDashboardSummaryUseCase(uow).execute(
        GetDashboardSummaryQuery(
            business_id=business_id, start_date=date(2026, 1, 1), end_date=date(2026, 1, 31)
        )
    )

    assert summary.total_revenue == Decimal("0")
    assert summary.outstanding_receivables == Decimal("100.00")


async def test_fully_paid_sales_excluded_from_outstanding_receivables() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    sale = await CreateSaleUseCase(uow).execute(make_sale_command(business_id))
    await RecordSalePaymentUseCase(uow).execute(
        RecordSalePaymentCommand(business_id=business_id, sale_id=sale.id, amount=Decimal("100"))
    )

    summary = await GetDashboardSummaryUseCase(uow).execute(
        GetDashboardSummaryQuery(business_id=business_id)
    )

    assert summary.outstanding_receivables == Decimal("0")
    assert summary.total_revenue == Decimal("100.00")
