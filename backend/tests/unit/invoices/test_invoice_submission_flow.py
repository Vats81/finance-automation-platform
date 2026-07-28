"""Application-layer, fake-repository test of the full submit -> (simulated)
OCR -> 2-way match -> status pipeline, wiring SubmitInvoiceUseCase and
RecordOcrResultUseCase together exactly as workers/tasks/ocr_tasks.py does
in production. No real Postgres/Celery/outbox involved — see
tests/integration/test_invoice_submission_flow.py (added once testcontainers
infra lands) for the true end-to-end version through the API and outbox.
"""

import uuid
from decimal import Decimal

from app.invoices.application.commands.record_ocr_result import RecordOcrResultCommand, RecordOcrResultUseCase
from app.invoices.application.commands.submit_invoice import (
    SubmitInvoiceCommand,
    SubmitInvoiceLineItemInput,
    SubmitInvoiceUseCase,
)
from app.invoices.domain.value_objects import InvoiceStatus
from app.invoices.infrastructure.document_processing_client import SimulatedDocumentProcessingClient
from app.purchase_orders.application.commands.create_purchase_order import (
    CreatePurchaseOrderCommand,
    CreatePurchaseOrderUseCase,
    LineItemInput,
)
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


async def test_matching_invoice_transitions_to_matched() -> None:
    uow = FakeUnitOfWork()
    vendor_id = uuid.uuid4()

    po_use_case = CreatePurchaseOrderUseCase(uow)
    po = await po_use_case.execute(
        CreatePurchaseOrderCommand(
            vendor_id=vendor_id,
            line_items=[
                LineItemInput(
                    line_number=1, description="Widgets", quantity=Decimal("10"), unit_price=Decimal("5.00")
                )
            ],
        )
    )

    submit_use_case = SubmitInvoiceUseCase(uow)
    invoice = await submit_use_case.execute(
        SubmitInvoiceCommand(
            invoice_number="INV-100",
            vendor_id=vendor_id,
            po_id=po.id,
            line_items=[
                SubmitInvoiceLineItemInput(
                    line_number=1, description="Widgets", quantity=Decimal("10"), unit_price=Decimal("5.00")
                )
            ],
        )
    )
    assert invoice.status == InvoiceStatus.SUBMITTED

    ocr_use_case = RecordOcrResultUseCase(uow, SimulatedDocumentProcessingClient())
    result = await ocr_use_case.execute(RecordOcrResultCommand(invoice_id=invoice.id))

    assert result.status == InvoiceStatus.MATCHED
    assert result.match_discrepancies == []


async def test_mismatched_invoice_transitions_to_match_exception() -> None:
    uow = FakeUnitOfWork()
    vendor_id = uuid.uuid4()

    po = await CreatePurchaseOrderUseCase(uow).execute(
        CreatePurchaseOrderCommand(
            vendor_id=vendor_id,
            line_items=[
                LineItemInput(
                    line_number=1, description="Widgets", quantity=Decimal("10"), unit_price=Decimal("5.00")
                )
            ],
        )
    )

    invoice = await SubmitInvoiceUseCase(uow).execute(
        SubmitInvoiceCommand(
            invoice_number="INV-101",
            vendor_id=vendor_id,
            po_id=po.id,
            line_items=[
                SubmitInvoiceLineItemInput(
                    line_number=1,
                    description="Widgets",
                    quantity=Decimal("12"),  # claims more than the PO
                    unit_price=Decimal("5.00"),
                )
            ],
        )
    )

    result = await RecordOcrResultUseCase(uow, SimulatedDocumentProcessingClient()).execute(
        RecordOcrResultCommand(invoice_id=invoice.id)
    )

    assert result.status == InvoiceStatus.MATCH_EXCEPTION
    assert len(result.match_discrepancies) > 0
