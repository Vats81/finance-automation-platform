import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from app.dashboard.application.queries.get_forecast import GetForecastQuery, GetForecastUseCase
from app.expenses.application.commands.create_expense import CreateExpenseCommand, CreateExpenseUseCase
from app.expenses.domain.value_objects import PaymentMethod
from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
from tests.fakes.fake_ports import FakeClock
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

# "Now" is mid-July 2026, so the last *completed* month is June — the
# 6-month history window is Jan-Jun 2026, and the 3 forecast points are
# Jul/Aug/Sep 2026.
_NOW = datetime(2026, 7, 15, tzinfo=timezone.utc)
_HISTORY_MONTHS_2026 = [date(2026, m, 1) for m in range(1, 7)]


def make_sale_command(business_id: uuid.UUID, amount: Decimal, invoice_date: date) -> CreateSaleCommand:
    return CreateSaleCommand(
        business_id=business_id,
        invoice_number=f"INV-{invoice_date.isoformat()}",
        invoice_date=invoice_date,
        line_items=[
            CreateSaleLineItemInput(
                line_number=1, description="Item", quantity=Decimal("1"), unit_price=amount
            )
        ],
    )


def make_expense_command(
    business_id: uuid.UUID, amount: Decimal, expense_date: date
) -> CreateExpenseCommand:
    return CreateExpenseCommand(
        business_id=business_id,
        expense_date=expense_date,
        category="Rent",
        description="Office rent",
        amount=amount,
        payment_method=PaymentMethod.BANK_TRANSFER,
    )


async def test_linear_increasing_revenue_projects_exact_values() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    for i, month_start in enumerate(_HISTORY_MONTHS_2026):
        amount = Decimal(str(100 * (i + 1)))  # 100, 200, ..., 600
        await CreateSaleUseCase(uow).execute(
            make_sale_command(business_id, amount, month_start.replace(day=15))
        )

    forecast = await GetForecastUseCase(uow, FakeClock(_NOW)).execute(
        GetForecastQuery(business_id=business_id)
    )

    assert forecast.history_months_used == 6
    assert [p.period_start for p in forecast.points] == [
        date(2026, 7, 1),
        date(2026, 8, 1),
        date(2026, 9, 1),
    ]
    assert [p.projected_revenue for p in forecast.points] == [
        Decimal("700.00"),
        Decimal("800.00"),
        Decimal("900.00"),
    ]
    assert all(p.projected_expenses == Decimal("0.00") for p in forecast.points)
    assert forecast.points[0].projected_net_profit == Decimal("700.00")


async def test_declining_revenue_projection_floored_at_zero() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    for i, month_start in enumerate(_HISTORY_MONTHS_2026):
        amount = Decimal(str(500 - 100 * i))  # 500, 400, ..., 0
        await CreateSaleUseCase(uow).execute(
            make_sale_command(business_id, amount, month_start.replace(day=15))
        )

    forecast = await GetForecastUseCase(uow, FakeClock(_NOW)).execute(
        GetForecastQuery(business_id=business_id)
    )

    # A perfectly linear extrapolation would go negative (-100, -200, -300)
    # from x=6 onward — every projected point must be floored at 0 instead.
    assert all(p.projected_revenue == Decimal("0.00") for p in forecast.points)


async def test_no_activity_produces_zero_projection_without_crashing() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    forecast = await GetForecastUseCase(uow, FakeClock(_NOW)).execute(
        GetForecastQuery(business_id=business_id)
    )

    assert forecast.history_months_used == 6
    assert len(forecast.points) == 3
    assert all(
        p.projected_revenue == Decimal("0.00")
        and p.projected_expenses == Decimal("0.00")
        and p.projected_net_profit == Decimal("0.00")
        for p in forecast.points
    )


async def test_current_month_activity_excluded_from_regression_input() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    # Dated in the current (still in-progress) month at _NOW — should not
    # leak into the Jan-Jun history window used for the regression.
    await CreateSaleUseCase(uow).execute(
        make_sale_command(business_id, Decimal("5000"), date(2026, 7, 10))
    )

    forecast = await GetForecastUseCase(uow, FakeClock(_NOW)).execute(
        GetForecastQuery(business_id=business_id)
    )

    assert all(p.projected_revenue == Decimal("0.00") for p in forecast.points)


async def test_projected_net_profit_can_go_negative_and_is_not_floored() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    for month_start in _HISTORY_MONTHS_2026:
        await CreateSaleUseCase(uow).execute(
            make_sale_command(business_id, Decimal("100"), month_start.replace(day=15))
        )
        await CreateExpenseUseCase(uow).execute(
            make_expense_command(business_id, Decimal("300"), month_start.replace(day=20))
        )

    forecast = await GetForecastUseCase(uow, FakeClock(_NOW)).execute(
        GetForecastQuery(business_id=business_id)
    )

    assert all(p.projected_revenue == Decimal("100.00") for p in forecast.points)
    assert all(p.projected_expenses == Decimal("300.00") for p in forecast.points)
    assert all(p.projected_net_profit == Decimal("-200.00") for p in forecast.points)
