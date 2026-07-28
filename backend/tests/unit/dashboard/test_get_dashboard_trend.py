import uuid
from datetime import date
from decimal import Decimal

from app.dashboard.application.queries.get_dashboard_trend import (
    GetDashboardTrendQuery,
    GetDashboardTrendUseCase,
)
from app.expenses.application.commands.create_expense import CreateExpenseCommand, CreateExpenseUseCase
from app.expenses.domain.value_objects import PaymentMethod
from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
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


async def test_day_granularity_buckets_a_sale_on_the_correct_day() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    await CreateSaleUseCase(uow).execute(
        make_sale_command(business_id, invoice_date=date(2026, 1, 15))
    )

    trend = await GetDashboardTrendUseCase(uow).execute(
        GetDashboardTrendQuery(
            business_id=business_id, start_date=date(2026, 1, 1), end_date=date(2026, 1, 31)
        )
    )

    assert trend.granularity == "day"
    assert len(trend.points) == 31
    point = next(p for p in trend.points if p.period_start == date(2026, 1, 15))
    assert point.revenue == Decimal("100.00")
    other_points = [p for p in trend.points if p.period_start != date(2026, 1, 15)]
    assert all(p.revenue == Decimal("0") for p in other_points)


async def test_month_granularity_groups_sales_within_the_same_month() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    await CreateSaleUseCase(uow).execute(
        make_sale_command(business_id, invoice_number="A", invoice_date=date(2026, 1, 5))
    )
    await CreateSaleUseCase(uow).execute(
        make_sale_command(business_id, invoice_number="B", invoice_date=date(2026, 1, 25))
    )

    trend = await GetDashboardTrendUseCase(uow).execute(
        GetDashboardTrendQuery(
            business_id=business_id, start_date=date(2026, 1, 1), end_date=date(2026, 3, 31)
        )
    )

    assert trend.granularity == "month"
    assert len(trend.points) == 3
    january = next(p for p in trend.points if p.period_start == date(2026, 1, 1))
    assert january.revenue == Decimal("200.00")


async def test_zero_activity_buckets_still_appear() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    trend = await GetDashboardTrendUseCase(uow).execute(
        GetDashboardTrendQuery(
            business_id=business_id, start_date=date(2026, 1, 1), end_date=date(2026, 3, 31)
        )
    )

    assert len(trend.points) == 3
    assert all(p.revenue == Decimal("0") and p.expenses == Decimal("0") for p in trend.points)


async def test_records_outside_range_excluded() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    await CreateSaleUseCase(uow).execute(
        make_sale_command(business_id, invoice_date=date(2025, 12, 31))
    )
    await CreateExpenseUseCase(uow).execute(
        make_expense_command(business_id, expense_date=date(2026, 2, 1))
    )

    trend = await GetDashboardTrendUseCase(uow).execute(
        GetDashboardTrendQuery(
            business_id=business_id, start_date=date(2026, 1, 1), end_date=date(2026, 1, 31)
        )
    )

    assert all(p.revenue == Decimal("0") and p.expenses == Decimal("0") for p in trend.points)


async def test_voided_sale_excluded() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    sale = await CreateSaleUseCase(uow).execute(
        make_sale_command(business_id, invoice_date=date(2026, 1, 15))
    )
    await VoidSaleUseCase(uow).execute(VoidSaleCommand(business_id=business_id, sale_id=sale.id))

    trend = await GetDashboardTrendUseCase(uow).execute(
        GetDashboardTrendQuery(
            business_id=business_id, start_date=date(2026, 1, 1), end_date=date(2026, 1, 31)
        )
    )

    assert all(p.revenue == Decimal("0") for p in trend.points)


async def test_granularity_boundary_at_31_days() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    at_boundary = await GetDashboardTrendUseCase(uow).execute(
        GetDashboardTrendQuery(
            business_id=business_id, start_date=date(2026, 1, 1), end_date=date(2026, 2, 1)
        )
    )
    assert at_boundary.granularity == "day"

    past_boundary = await GetDashboardTrendUseCase(uow).execute(
        GetDashboardTrendQuery(
            business_id=business_id, start_date=date(2026, 1, 1), end_date=date(2026, 2, 2)
        )
    )
    assert past_boundary.granularity == "month"


async def test_week_granularity_buckets_sale_into_monday_start_week() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    # 2026-01-14 is a Wednesday; its ISO week starts Monday 2026-01-12.
    await CreateSaleUseCase(uow).execute(
        make_sale_command(business_id, invoice_date=date(2026, 1, 14))
    )

    trend = await GetDashboardTrendUseCase(uow).execute(
        GetDashboardTrendQuery(
            business_id=business_id,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            granularity="week",
        )
    )

    assert trend.granularity == "week"
    week = next(p for p in trend.points if p.period_start == date(2026, 1, 12))
    assert week.revenue == Decimal("100.00")


async def test_week_granularity_spanning_a_month_boundary() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    # 2026-01-30 (Friday) falls in the week starting Monday 2026-01-26;
    # 2026-02-02 (Monday) starts its own week.
    await CreateSaleUseCase(uow).execute(
        make_sale_command(business_id, invoice_date=date(2026, 1, 30))
    )
    await CreateExpenseUseCase(uow).execute(
        make_expense_command(business_id, expense_date=date(2026, 2, 2))
    )

    trend = await GetDashboardTrendUseCase(uow).execute(
        GetDashboardTrendQuery(
            business_id=business_id,
            start_date=date(2026, 1, 28),
            end_date=date(2026, 2, 2),
            granularity="week",
        )
    )

    assert [p.period_start for p in trend.points] == [date(2026, 1, 26), date(2026, 2, 2)]
    first_week = trend.points[0]
    second_week = trend.points[1]
    assert first_week.revenue == Decimal("100.00")
    assert second_week.expenses == Decimal("30.00")


async def test_explicit_granularity_overrides_auto_infer() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    # A 10-day span would auto-infer "day", but an explicit granularity
    # takes precedence.
    trend = await GetDashboardTrendUseCase(uow).execute(
        GetDashboardTrendQuery(
            business_id=business_id,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
            granularity="month",
        )
    )

    assert trend.granularity == "month"
    assert len(trend.points) == 1
    assert trend.points[0].period_start == date(2026, 1, 1)
