import io
from datetime import date, timedelta
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.dashboard.application.queries.get_dashboard_trend import DashboardTrend, Granularity

_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]  # fmt: skip
_MONTH_ABBR = [name[:3] for name in _MONTH_NAMES]


def _format_currency(amount: Decimal) -> str:
    return f"${amount:,.2f}"


def _format_short_date(value: date, *, with_year: bool) -> str:
    # Built manually rather than via strftime's "%-d"/"%#d" no-padding
    # flags — those are glibc/Windows-specific in opposite, incompatible
    # ways, so neither is portable across the platforms this runs on.
    label = f"{_MONTH_ABBR[value.month - 1]} {value.day}"
    return f"{label}, {value.year}" if with_year else label


def _format_period_label(period_start: date, granularity: Granularity) -> str:
    if granularity == "month":
        return f"{_MONTH_NAMES[period_start.month - 1]} {period_start.year}"
    if granularity == "day":
        return _format_short_date(period_start, with_year=True)
    end = period_start + timedelta(days=6)
    start_label = _format_short_date(period_start, with_year=False)
    end_label = _format_short_date(end, with_year=True)
    return f"{start_label} - {end_label}"


def generate_profit_loss_pdf(business_name: str, trend: DashboardTrend) -> bytes:
    """Renders the same Profit & Loss breakdown as the Reports page's
    on-screen table (frontend/src/app/app/(shell)/reports/page.tsx) as a
    downloadable PDF — same period-label formatting logic, a third copy per
    this codebase's established per-layer duplication convention (see
    dashboard/page.tsx's and reports/page.tsx's own toISODate/getPeriodRange
    duplication for precedent). Pure function: takes already-fetched domain
    data, does no I/O itself, so it's cheap to unit test.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()

    total_revenue = sum((p.revenue for p in trend.points), Decimal("0"))
    total_expenses = sum((p.expenses for p in trend.points), Decimal("0"))
    net_profit = total_revenue - total_expenses

    header = ["Period", "Revenue", "Expenses", "Net Profit"]
    rows = [
        [
            _format_period_label(p.period_start, trend.granularity),
            _format_currency(p.revenue),
            _format_currency(p.expenses),
            _format_currency(p.revenue - p.expenses),
        ]
        for p in trend.points
    ]
    totals_row = [
        "Total",
        _format_currency(total_revenue),
        _format_currency(total_expenses),
        _format_currency(net_profit),
    ]
    table_data = [header, *rows, totals_row]

    table = Table(table_data, colWidths=[2.2 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#cbd5e1")),
                ("LINEABOVE", (0, -1), (-1, -1), 1.5, colors.HexColor("#94a3b8")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elements = [
        Paragraph(business_name, styles["Title"]),
        Paragraph("Profit &amp; Loss", styles["Heading2"]),
        Spacer(1, 0.25 * inch),
        table,
    ]
    doc.build(elements)
    return buffer.getvalue()
