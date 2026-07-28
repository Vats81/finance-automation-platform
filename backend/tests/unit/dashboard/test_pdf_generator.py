from datetime import date
from decimal import Decimal

from app.dashboard.application.pdf_generator import generate_profit_loss_pdf
from app.dashboard.application.queries.get_dashboard_trend import DashboardTrend, TrendPoint


def make_trend(granularity="month") -> DashboardTrend:
    return DashboardTrend(
        granularity=granularity,
        points=[
            TrendPoint(period_start=date(2026, 5, 1), revenue=Decimal("400.00"), expenses=Decimal("0")),
            TrendPoint(period_start=date(2026, 6, 1), revenue=Decimal("250.00"), expenses=Decimal("80.00")),
            TrendPoint(period_start=date(2026, 7, 1), revenue=Decimal("500.00"), expenses=Decimal("150.00")),
        ],
    )


def test_generates_a_real_pdf_with_month_granularity() -> None:
    pdf_bytes = generate_profit_loss_pdf("Jane's Diner Supplies", make_trend("month"))

    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 500


def test_generates_a_real_pdf_with_day_granularity() -> None:
    trend = DashboardTrend(
        granularity="day",
        points=[TrendPoint(period_start=date(2026, 7, 20), revenue=Decimal("500.00"), expenses=Decimal("0"))],
    )

    pdf_bytes = generate_profit_loss_pdf("Jane's Diner Supplies", trend)

    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 500


def test_generates_a_real_pdf_with_week_granularity() -> None:
    trend = DashboardTrend(
        granularity="week",
        points=[TrendPoint(period_start=date(2026, 7, 20), revenue=Decimal("500.00"), expenses=Decimal("0"))],
    )

    pdf_bytes = generate_profit_loss_pdf("Jane's Diner Supplies", trend)

    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 500


def test_handles_empty_points_without_crashing() -> None:
    trend = DashboardTrend(granularity="month", points=[])

    pdf_bytes = generate_profit_loss_pdf("Jane's Diner Supplies", trend)

    assert pdf_bytes.startswith(b"%PDF-")
