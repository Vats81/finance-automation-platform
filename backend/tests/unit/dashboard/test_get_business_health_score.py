import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.dashboard.application.queries.get_business_health_score import (
    GetBusinessHealthScoreQuery,
    GetBusinessHealthScoreUseCase,
)
from app.expenses.application.commands.create_expense import CreateExpenseCommand, CreateExpenseUseCase
from app.expenses.domain.value_objects import PaymentMethod
from app.inventory.application.commands.create_product import CreateProductCommand, CreateProductUseCase
from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
from app.sales.application.commands.record_payment import RecordSalePaymentCommand, RecordSalePaymentUseCase
from tests.fakes.fake_ports import FakeClock
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

_NOW = datetime(2026, 7, 24, tzinfo=timezone.utc)


async def _make_business(uow: FakeUnitOfWork) -> uuid.UUID:
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Test Business")
    )
    return business.id


async def _make_sale(
    uow: FakeUnitOfWork, business_id: uuid.UUID, *, invoice_date: date, amount: Decimal, invoice_number: str
):
    return await CreateSaleUseCase(uow).execute(
        CreateSaleCommand(
            business_id=business_id,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            line_items=[
                CreateSaleLineItemInput(
                    line_number=1, description="Item", quantity=Decimal("1"), unit_price=amount
                )
            ],
        )
    )


async def test_healthy_growing_business_scores_excellent() -> None:
    uow = FakeUnitOfWork()
    business_id = await _make_business(uow)
    # outstanding_receivables (used by receivables_health) is a point-in-time
    # balance across ALL sales, not just this month's — so the June sale
    # must be paid off too, or it'd still show up as money owed today.
    june_sale = await _make_sale(
        uow, business_id, invoice_date=date(2026, 6, 15), amount=Decimal("500"), invoice_number="JUNE-1"
    )
    await RecordSalePaymentUseCase(uow).execute(
        RecordSalePaymentCommand(business_id=business_id, sale_id=june_sale.id, amount=Decimal("500"))
    )
    july_sale = await _make_sale(
        uow, business_id, invoice_date=date(2026, 7, 10), amount=Decimal("1000"), invoice_number="JULY-1"
    )
    await RecordSalePaymentUseCase(uow).execute(
        RecordSalePaymentCommand(business_id=business_id, sale_id=july_sale.id, amount=Decimal("1000"))
    )
    await CreateProductUseCase(uow).execute(
        CreateProductCommand(
            business_id=business_id,
            name="Widget",
            sku="W-1",
            selling_price=Decimal("10"),
            purchase_cost=Decimal("5"),
            current_quantity=Decimal("100"),
            minimum_stock_level=Decimal("5"),
        )
    )

    result = await GetBusinessHealthScoreUseCase(uow, FakeClock(_NOW)).execute(
        GetBusinessHealthScoreQuery(business_id=business_id)
    )

    assert result.overall_score == 100
    assert result.label == "Excellent"
    assert result.breakdown["profitability"] == 1.0
    assert result.breakdown["revenue_trend"] == 1.0
    assert result.breakdown["receivables_health"] == 1.0
    assert result.breakdown["inventory_health"] == 1.0


async def test_lossy_declining_business_scores_critical() -> None:
    uow = FakeUnitOfWork()
    business_id = await _make_business(uow)
    await _make_sale(
        uow, business_id, invoice_date=date(2026, 6, 15), amount=Decimal("2000"), invoice_number="JUNE-1"
    )
    await _make_sale(
        uow, business_id, invoice_date=date(2026, 7, 10), amount=Decimal("500"), invoice_number="JULY-1"
    )
    await CreateExpenseUseCase(uow).execute(
        CreateExpenseCommand(
            business_id=business_id,
            expense_date=date(2026, 7, 12),
            category="Rent",
            description="Rent",
            amount=Decimal("800"),
            payment_method=PaymentMethod.CASH,
        )
    )
    await CreateProductUseCase(uow).execute(
        CreateProductCommand(
            business_id=business_id,
            name="Widget",
            sku="W-1",
            selling_price=Decimal("10"),
            purchase_cost=Decimal("5"),
            current_quantity=Decimal("1"),
            minimum_stock_level=Decimal("10"),
        )
    )

    result = await GetBusinessHealthScoreUseCase(uow, FakeClock(_NOW)).execute(
        GetBusinessHealthScoreQuery(business_id=business_id)
    )

    assert result.overall_score == 0
    assert result.label == "Critical"
    assert result.breakdown["profitability"] == 0.0
    assert result.breakdown["revenue_trend"] == 0.0
    assert result.breakdown["receivables_health"] == 0.0
    assert result.breakdown["inventory_health"] == 0.0


async def test_brand_new_business_excludes_inapplicable_categories() -> None:
    uow = FakeUnitOfWork()
    business_id = await _make_business(uow)

    result = await GetBusinessHealthScoreUseCase(uow, FakeClock(_NOW)).execute(
        GetBusinessHealthScoreQuery(business_id=business_id)
    )

    assert result.breakdown["profitability"] is None
    assert result.breakdown["inventory_health"] is None
    assert result.breakdown["revenue_trend"] == 0.5
    assert result.breakdown["receivables_health"] == 1.0
    assert result.overall_score == 75
    assert result.label == "Good"


async def test_revenue_from_zero_last_month_scores_full_trend() -> None:
    uow = FakeUnitOfWork()
    business_id = await _make_business(uow)
    await _make_sale(
        uow, business_id, invoice_date=date(2026, 7, 10), amount=Decimal("100"), invoice_number="JULY-1"
    )

    result = await GetBusinessHealthScoreUseCase(uow, FakeClock(_NOW)).execute(
        GetBusinessHealthScoreQuery(business_id=business_id)
    )

    assert result.breakdown["revenue_trend"] == 1.0
