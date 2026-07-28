from dataclasses import dataclass

from app.invoices.domain.entities import Invoice
from app.purchase_orders.domain.entities import PurchaseOrder


@dataclass(frozen=True)
class MatchResult:
    is_matched: bool
    discrepancies: list[str]


class TwoWayMatchService:
    """Domain service: reconciles a submitted Invoice against the
    PurchaseOrder it references — "two-way" meaning invoice vs. PO only (no
    goods-receipt/3-way match in this foundation slice; see
    purchase_orders/domain/matching in PHASE2_ROADMAP.md for that
    extension point). Pure function of two aggregates already loaded by the
    caller (record_ocr_result use case) — this service never touches a
    repository itself.
    """

    @staticmethod
    def match(invoice: Invoice, purchase_order: PurchaseOrder) -> MatchResult:
        discrepancies: list[str] = []

        if invoice.vendor_id != purchase_order.vendor_id:
            discrepancies.append("Invoice vendor does not match purchase order vendor")

        for line in invoice.line_items:
            po_line = purchase_order.get_line(line.line_number)
            if po_line is None:
                discrepancies.append(f"Line {line.line_number}: no matching PO line")
                continue
            if line.quantity != po_line.quantity:
                discrepancies.append(
                    f"Line {line.line_number}: quantity {line.quantity} != PO quantity {po_line.quantity}"
                )
            if line.unit_price != po_line.unit_price:
                discrepancies.append(
                    f"Line {line.line_number}: unit price {line.unit_price} "
                    f"!= PO unit price {po_line.unit_price}"
                )

        if invoice.total_amount != purchase_order.total_amount:
            discrepancies.append(
                f"Invoice total {invoice.total_amount} != PO total {purchase_order.total_amount}"
            )

        return MatchResult(is_matched=not discrepancies, discrepancies=discrepancies)
