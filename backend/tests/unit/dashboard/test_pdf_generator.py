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


# ---- what is actually printed (decoded from the PDF, not just "it is a PDF")


def pdf_text(pdf: bytes) -> str:
    import base64
    import re
    import zlib

    chunks = []
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", pdf, re.S):
        data = match.group(1).strip().removesuffix(b"~>")
        for decode in (lambda d: zlib.decompress(base64.a85decode(d)), zlib.decompress):
            try:
                chunks.append(decode(data).decode("latin-1"))
                break
            except Exception:  # noqa: BLE001, S112 - not every stream is page content
                continue
    return " ".join(re.findall(r"\((.*?)\)\s*Tj", " ".join(chunks)))


def test_the_pdf_shows_the_business_period_and_the_dashboard_totals() -> None:
    trend = DashboardTrend(
        granularity="month",
        points=[
            TrendPoint(
                period_start=date(2026, 10, 1), revenue=Decimal("3250.00"), expenses=Decimal("1585.50")
            )
        ],
    )

    text = pdf_text(
        generate_profit_loss_pdf(
            "[QA] Demo Bakery", trend, start_date=date(2026, 10, 1), end_date=date(2026, 10, 31)
        )
    )

    for expected in (
        "[QA] Demo Bakery",
        "2026-10-01 to 2026-10-31",
        "USD",
        "October 2026",
        "$3,250.00",
        "$1,585.50",
        "$1,664.50",
    ):
        assert expected in text, (expected, text)


def test_losses_print_as_negative_dollars_not_dollar_negative() -> None:
    trend = DashboardTrend(
        granularity="month",
        points=[
            TrendPoint(period_start=date(2026, 10, 1), revenue=Decimal("100.00"), expenses=Decimal("250.50"))
        ],
    )

    text = pdf_text(generate_profit_loss_pdf("Loss Co", trend))

    assert "-$150.50" in text
    assert "$-150.50" not in text


def test_business_names_with_markup_characters_do_not_break_or_inject_into_the_pdf() -> None:
    pdf = generate_profit_loss_pdf("Smith & Sons <b>Ltd</b> </para>", make_trend("month"))

    assert pdf.startswith(b"%PDF-")
    printed = pdf_text(pdf).replace(" ", "")
    assert "Smith&Sons<b>Ltd</b></para>" in printed  # shown literally, not interpreted as markup
