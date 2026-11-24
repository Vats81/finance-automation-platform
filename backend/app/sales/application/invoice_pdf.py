import io
from datetime import date
from decimal import Decimal
from urllib.parse import quote
from xml.sax.saxutils import escape

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.business.domain.entities import Business
from app.customers.domain.entities import Customer
from app.sales.domain.entities import Sale
from app.sales.domain.value_objects import SaleStatus
from app.shared.domain.gst import GST_STATES, split_tax
from app.shared.domain.money_format import format_money
from app.shared.domain.money_words import rupees_in_words

_INK = colors.HexColor("#0f172a")
_MUTED = colors.HexColor("#64748b")
_RULE = colors.HexColor("#cbd5e1")
_BAND = colors.HexColor("#f1f5f9")


def _state_name(code: str | None) -> str:
    return GST_STATES.get(code, "") if code else ""


def _fmt_date(value: date) -> str:
    return value.strftime("%d %b %Y")


def _plain(value: Decimal) -> str:
    """A quantity or rate without trailing zeros: 2.000 -> 2, 0.250 -> 0.25."""
    return format(value.normalize(), "f")


class _UpiQr(Flowable):
    """A UPI payment QR. Scanning it in any UPI app opens a payment to this business for the amount due."""

    def __init__(self, payload: str, size: float) -> None:
        super().__init__()
        self._widget = qr.QrCodeWidget(payload)
        self.width = self.height = size

    def draw(self) -> None:
        x0, y0, x1, y1 = self._widget.getBounds()
        drawing = Drawing(
            self.width,
            self.height,
            transform=[self.width / (x1 - x0), 0, 0, self.height / (y1 - y0), 0, 0],
        )
        drawing.add(self._widget)
        renderPDF.draw(drawing, self.canv, 0, 0)


def _upi_link(business: Business, sale: Sale, currency: str) -> str | None:
    if currency != "INR" or not business.upi_id:
        return None
    link = f"upi://pay?pa={quote(business.upi_id)}&pn={quote(business.name)}&cu=INR"
    due = sale.outstanding_amount.amount
    if due > 0:
        link += f"&am={due:.2f}"
    return link + f"&tn={quote('Invoice ' + sale.invoice_number)}"


def generate_invoice_pdf(*, business: Business, sale: Sale, customer: Customer | None) -> bytes:
    """A printable invoice (a GST tax invoice when the lines carry GST rates). Pure: takes already-fetched
    domain objects and does no I/O. Rupee amounts print as "Rs." because the built-in PDF fonts have no rupee
    sign.
    """
    currency = business.currency

    def money(value: Decimal) -> str:
        return format_money(value, currency, plain=True)

    base = getSampleStyleSheet()["Normal"]
    small = ParagraphStyle("small", parent=base, fontSize=8.5, leading=11, textColor=_INK)
    muted = ParagraphStyle("muted", parent=small, textColor=_MUTED)
    body = ParagraphStyle("body", parent=small, fontSize=9.5, leading=12.5)
    bold = ParagraphStyle("bold", parent=body, fontName="Helvetica-Bold")
    right = ParagraphStyle("right", parent=body, alignment=2)
    right_bold = ParagraphStyle("right_bold", parent=right, fontName="Helvetica-Bold")
    title = ParagraphStyle("title", parent=bold, fontSize=17, leading=21)
    head = ParagraphStyle("head", parent=small, fontName="Helvetica-Bold", textColor=_MUTED)
    head_right = ParagraphStyle("head_right", parent=head, alignment=2)

    def p(text: str, style: ParagraphStyle = body) -> Paragraph:
        return Paragraph(escape(text).replace("\n", "<br/>"), style)

    has_gst = bool(sale.gst_groups)
    seller_state = business.state_code
    place = sale.place_of_supply or seller_state
    inter_state = bool(seller_state and place and seller_state != place)

    # Seller block (left) and invoice facts (right)
    seller_lines = [p(business.name, title)]
    address_bits = [business.address_line, " ".join(x for x in (business.city, business.pincode) if x)]
    address = ", ".join(x for x in address_bits if x)
    if address:
        seller_lines.append(p(address, body))
    if seller_state:
        seller_lines.append(p(f"{_state_name(seller_state)} ({seller_state})", body))
    if business.phone:
        seller_lines.append(p(f"Phone: {business.phone}", body))
    if business.gstin:
        seller_lines.append(p(f"GSTIN: {business.gstin}", bold))

    facts: list[list[Paragraph]] = [
        [p("TAX INVOICE" if has_gst else "INVOICE", bold), p("", body)],
        [p("Invoice no.", muted), p(sale.invoice_number, bold)],
        [p("Date", muted), p(_fmt_date(sale.invoice_date), body)],
    ]
    if sale.due_date:
        facts.append([p("Due date", muted), p(_fmt_date(sale.due_date), body)])
    if has_gst and place:
        facts.append([p("Place of supply", muted), p(f"{_state_name(place)} ({place})", body)])
    facts_table = Table(facts, colWidths=[30 * mm, 45 * mm])
    facts_table.setStyle(
        TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)])
    )

    top = Table([[seller_lines, facts_table]], colWidths=[105 * mm, 75 * mm])
    top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))

    # Bill to
    bill = [p("BILL TO", head)]
    if customer is not None:
        bill.append(p(customer.name, bold))
        if customer.address:
            a = customer.address
            bill.append(p(f"{a.street}, {a.city}, {a.state} {a.postal_code}", body))
        if customer.phone:
            bill.append(p(f"Phone: {customer.phone}", body))
        if customer.gst_number:
            bill.append(p(f"GSTIN: {customer.gst_number}", body))
    else:
        bill.append(p("Walk-in customer", body))

    # Line items
    columns = [("#", False), ("Description", False)]
    if has_gst:
        columns.append(("HSN/SAC", False))
    columns += [("Qty", True), ("Rate", True)]
    if has_gst:
        columns.append(("GST %", True))
    columns.append(("Amount", True))
    rows: list[list] = [[p(name, head_right if align_right else head) for name, align_right in columns]]
    for item in sale.line_items:
        row: list = [p(str(item.line_number), body), p(item.description, body)]
        if has_gst:
            row.append(p(item.hsn_code or "-", body))
        row += [p(_plain(item.quantity), right), p(money(item.unit_price.amount), right)]
        if has_gst:
            row.append(p(f"{_plain(item.gst_rate)}%" if item.gst_rate is not None else "-", right))
        row.append(p(money(item.line_total.amount), right))
        rows.append(row)
    widths = (
        [8 * mm, 62 * mm, 22 * mm, 14 * mm, 26 * mm, 16 * mm, 32 * mm]
        if has_gst
        else [8 * mm, 92 * mm, 20 * mm, 26 * mm, 34 * mm]
    )
    items = Table(rows, colWidths=widths, repeatRows=1)
    items.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _BAND),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, _RULE),
                ("LINEBELOW", (0, 1), (-1, -1), 0.3, _RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    # Tax summary (one row per rate) and the totals
    summary_flow: list = []
    taxed = [g for g in sale.gst_groups if g.rate > 0]
    if has_gst:
        if inter_state:
            sh = ["GST %", "Taxable value", "IGST", "Total tax"]
        else:
            sh = ["GST %", "Taxable value", "CGST", "SGST", "Total tax"]
        srows: list[list] = [[p(h, head_right) for h in sh]]
        for g in sale.gst_groups:
            cgst, sgst, igst = split_tax(g.tax.amount, inter_state=inter_state)
            cells = [f"{_plain(g.rate)}%", money(g.taxable_value.amount)]
            cells += [money(igst)] if inter_state else [money(cgst), money(sgst)]
            cells.append(money(g.tax.amount))
            srows.append([p(c, right) for c in cells])
        sw = (
            [22 * mm, 40 * mm, 34 * mm, 34 * mm]
            if inter_state
            else [22 * mm, 38 * mm, 28 * mm, 28 * mm, 28 * mm]
        )
        summary = Table(srows, colWidths=sw)
        summary.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _BAND),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.3, _RULE),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        summary_flow = [Spacer(1, 6 * mm), p("GST SUMMARY", head), Spacer(1, 1.5 * mm), summary]

    totals: list[list] = [[p("Subtotal", body), p(money(sale.subtotal.amount), right)]]
    if sale.discount.amount > 0:
        totals.append([p("Discount", body), p("-" + money(sale.discount.amount), right)])
    if has_gst:
        if taxed:
            if inter_state:
                totals.append([p("IGST", body), p(money(sale.tax.amount), right)])
            else:
                cgst_total = sgst_total = Decimal("0")
                for g in taxed:
                    c, s, _ = split_tax(g.tax.amount, inter_state=False)
                    cgst_total += c
                    sgst_total += s
                totals.append([p("CGST", body), p(money(cgst_total), right)])
                totals.append([p("SGST", body), p(money(sgst_total), right)])
    elif sale.tax.amount > 0:
        totals.append([p("Tax", body), p(money(sale.tax.amount), right)])
    totals.append([p("Total", bold), p(money(sale.total_amount.amount), right_bold)])
    if sale.amount_received.amount > 0:
        totals.append([p("Received", body), p("-" + money(sale.amount_received.amount), right)])
        totals.append([p("Balance due", bold), p(money(sale.outstanding_amount.amount), right_bold)])
    totals_table = Table(totals, colWidths=[40 * mm, 36 * mm])
    totals_table.setStyle(
        TableStyle(
            [
                (
                    "LINEABOVE",
                    (0, -1 if sale.amount_received.amount <= 0 else -3),
                    (-1, -1 if sale.amount_received.amount <= 0 else -3),
                    0.6,
                    _INK,
                ),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )

    story: list = [
        top,
        Spacer(1, 6 * mm),
        Table(
            [[bill]],
            colWidths=[180 * mm],
            style=[
                ("BOX", (0, 0), (-1, -1), 0.4, _RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ],
        ),
        Spacer(1, 5 * mm),
        items,
        Spacer(1, 4 * mm),
    ]
    story.append(
        Table(
            [["", totals_table]],
            colWidths=[104 * mm, 76 * mm],
            style=[
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ],
        )
    )
    story += summary_flow
    if currency == "INR":
        story += [Spacer(1, 5 * mm), p("Amount in words: " + rupees_in_words(sale.total_amount.amount), body)]

    # Payment and notes
    link = _upi_link(business, sale, currency)
    pay_cells: list = []
    if link and sale.status != SaleStatus.VOID:
        pay_cells.append(
            [
                _UpiQr(link, 26 * mm),
                [p("Pay by UPI", bold), p(business.upi_id or "", body), p("Scan with any UPI app", muted)],
            ]
        )
    if pay_cells:
        pay = Table(pay_cells, colWidths=[30 * mm, 80 * mm])
        pay.setStyle(
            TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)])
        )
        story += [Spacer(1, 6 * mm), pay]
    if sale.notes:
        story += [Spacer(1, 5 * mm), p("NOTES", head), p(sale.notes, body)]
    story += [Spacer(1, 8 * mm), p("This is a computer generated invoice.", muted)]

    void = sale.status == SaleStatus.VOID

    def on_page(canvas, _doc) -> None:  # noqa: ANN001
        if void:
            canvas.saveState()
            canvas.setFont("Helvetica-Bold", 90)
            canvas.setFillColor(colors.Color(0.8, 0.1, 0.1, alpha=0.18))
            canvas.translate(105 * mm, 150 * mm)
            canvas.rotate(35)
            canvas.drawCentredString(0, 0, "VOID")
            canvas.restoreState()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Invoice {sale.invoice_number}",
        author=business.name,
    )
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buffer.getvalue()
