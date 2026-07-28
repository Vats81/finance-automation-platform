import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.invoices.domain.events import (
    InvoiceApproved,
    InvoiceMatched,
    InvoiceRejected,
    InvoiceSubmitted,
    MatchExceptionRaised,
)
from app.invoices.domain.exceptions import EmptyInvoiceException, InvalidInvoiceStateTransitionException
from app.invoices.domain.value_objects import InvoiceLineItem, InvoiceStatus
from app.shared.domain.aggregate_root import AggregateRoot
from app.shared.domain.value_objects import Money


class Invoice(AggregateRoot):
    """Own aggregate; references PurchaseOrder only by `po_id` (never loads
    or mutates it — see purchase_orders/domain/entities.py). Coordinated
    with ApprovalWorkflow (a separate aggregate — approvals/domain/entities.py)
    purely through domain events relayed via the outbox: InvoiceMatched
    triggers a workflow to start; ApprovalWorkflowCompleted (approvals
    context) drives mark_approved()/mark_rejected() here via an application
    command, never a direct cross-aggregate call.
    """

    def __init__(
        self,
        *,
        entity_id: uuid.UUID | None = None,
        invoice_number: str,
        vendor_id: uuid.UUID,
        po_id: uuid.UUID,
        line_items: list[InvoiceLineItem],
        document_reference: str | None = None,
        status: InvoiceStatus = InvoiceStatus.SUBMITTED,
        match_discrepancies: list[str] | None = None,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.invoice_number = invoice_number
        self.vendor_id = vendor_id
        self.po_id = po_id
        self.line_items = line_items
        self.document_reference = document_reference
        self.status = status
        self.match_discrepancies = match_discrepancies or []
        self.created_at = created_at or datetime.now(timezone.utc)

    @classmethod
    def submit(
        cls,
        *,
        invoice_number: str,
        vendor_id: uuid.UUID,
        po_id: uuid.UUID,
        line_items: list[InvoiceLineItem],
        document_reference: str | None = None,
    ) -> "Invoice":
        if not line_items:
            raise EmptyInvoiceException("An invoice requires at least one line item")

        invoice = cls(
            invoice_number=invoice_number,
            vendor_id=vendor_id,
            po_id=po_id,
            line_items=line_items,
            document_reference=document_reference,
        )
        invoice._record_event(
            InvoiceSubmitted(
                aggregate_id=invoice.id,
                invoice_number=invoice_number,
                vendor_id=str(vendor_id),
                po_id=str(po_id),
                total_amount_cents=invoice.total_amount.cents,
            )
        )
        return invoice

    def attach_document(self, document_reference: str) -> None:
        self.document_reference = document_reference

    @property
    def total_amount(self) -> Money:
        total = Money(amount=Decimal("0"))
        for item in self.line_items:
            total = total + item.line_total
        return total

    def _require_status(self, expected: InvoiceStatus) -> None:
        if self.status != expected:
            raise InvalidInvoiceStateTransitionException(
                f"Invoice {self.id} is {self.status.value}, expected {expected.value}"
            )

    def mark_matched(self) -> None:
        self._require_status(InvoiceStatus.SUBMITTED)
        self.status = InvoiceStatus.MATCHED
        self.match_discrepancies = []
        self._record_event(InvoiceMatched(aggregate_id=self.id, po_id=str(self.po_id)))

    def mark_match_exception(self, discrepancies: list[str]) -> None:
        self._require_status(InvoiceStatus.SUBMITTED)
        self.status = InvoiceStatus.MATCH_EXCEPTION
        self.match_discrepancies = discrepancies
        self._record_event(
            MatchExceptionRaised(aggregate_id=self.id, po_id=str(self.po_id), discrepancies=discrepancies)
        )

    def mark_pending_approval(self) -> None:
        self._require_status(InvoiceStatus.MATCHED)
        self.status = InvoiceStatus.PENDING_APPROVAL

    def mark_approved(self) -> None:
        self._require_status(InvoiceStatus.PENDING_APPROVAL)
        self.status = InvoiceStatus.APPROVED
        self._record_event(
            InvoiceApproved(
                aggregate_id=self.id,
                invoice_number=self.invoice_number,
                vendor_id=str(self.vendor_id),
                total_amount_cents=self.total_amount.cents,
            )
        )

    def mark_rejected(self, reason: str) -> None:
        self._require_status(InvoiceStatus.PENDING_APPROVAL)
        self.status = InvoiceStatus.REJECTED
        self._record_event(
            InvoiceRejected(aggregate_id=self.id, invoice_number=self.invoice_number, reason=reason)
        )
