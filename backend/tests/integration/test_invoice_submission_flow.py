"""Full-stack, full-flow test: real FastAPI app + real Postgres, driving
vendor -> PO -> invoice submission -> match -> approval -> payment
scheduling through actual HTTP calls.

The one exception: the async document-processing/matching hop that
production wires through RabbitMQ + a Celery worker (workers/tasks/ocr_tasks.py,
triggered by the outbox relay) is invoked directly here as a function call
instead of enqueued. Standing up a real broker + worker process inside a
test is disproportionate to what it would verify — the matching logic
itself is already covered by RecordOcrResultUseCase's own tests
(tests/unit/invoices/test_invoice_submission_flow.py) and by
TwoWayMatchService's unit tests. What this test verifies that those don't:
that the real HTTP API, real RBAC, and real Postgres persistence layer
correctly carry an invoice through every status transition end to end.
Requires Docker; skipped automatically otherwise.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.application.commands.start_approval_workflow import (
    StartApprovalWorkflowCommand,
    StartApprovalWorkflowUseCase,
)
from app.approvals.infrastructure.threshold_config import load_approval_threshold
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.config.settings import get_settings
from app.identity.infrastructure.models import UserModel
from app.invoices.application.commands.record_ocr_result import RecordOcrResultCommand, RecordOcrResultUseCase
from app.invoices.infrastructure.document_processing_client import SimulatedDocumentProcessingClient
from app.payments.application.commands.schedule_payment import SchedulePaymentCommand, SchedulePaymentUseCase
from tests.conftest import auth_header

pytestmark = pytest.mark.integration

CLERK = auth_header(oid="ap-clerk", email="clerk@example.com")
APPROVER = auth_header(oid="approver-1", email="approver@example.com")


async def _promote_to_role(db_session: AsyncSession, *, oid: str, role: str) -> None:
    """Test-only shortcut: there's no bootstrap "first admin" endpoint by
    design (role assignment itself requires an existing Finance Admin), so
    integration tests seed roles directly against the same session the
    `client` fixture is using.
    """
    await db_session.execute(update(UserModel).where(UserModel.entra_object_id == oid).values(role=role))
    await db_session.flush()


async def test_full_invoice_lifecycle_from_submission_to_payment(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # 1. Provision the two actors this flow needs.
    await client.get("/api/v1/me", headers=CLERK)
    await client.get("/api/v1/me", headers=APPROVER)
    await _promote_to_role(db_session, oid="approver-1", role="approver")

    # 2. Create a vendor and an open purchase order for it.
    vendor_resp = await client.post(
        "/api/v1/vendors",
        json={
            "legal_name": "Acme Supplies",
            "contact_email": "ap@acme.com",
            "tax_id": "12-3456789",
            "address": {"street": "1 St", "city": "City", "state": "ST", "postal_code": "00000"},
        },
        headers=CLERK,
    )
    vendor_id = vendor_resp.json()["id"]

    po_resp = await client.post(
        "/api/v1/purchase-orders",
        json={
            "vendor_id": vendor_id,
            "line_items": [
                {"line_number": 1, "description": "Widgets", "quantity": "10", "unit_price": "5.00"}
            ],
        },
        headers=CLERK,
    )
    po_id = po_resp.json()["id"]

    # 3. Submit an invoice that matches the PO exactly.
    invoice_resp = await client.post(
        "/api/v1/invoices",
        json={
            "invoice_number": "INV-E2E-001",
            "vendor_id": vendor_id,
            "po_id": po_id,
            "line_items": [
                {"line_number": 1, "description": "Widgets", "quantity": "10", "unit_price": "5.00"}
            ],
        },
        headers=CLERK,
    )
    assert invoice_resp.status_code == 201, invoice_resp.text
    invoice_id = invoice_resp.json()["id"]
    assert invoice_resp.json()["status"] == "submitted"

    uow = AppUnitOfWork(db_session)

    # 4. Run the document-processing/matching step (see module docstring).
    await RecordOcrResultUseCase(uow, SimulatedDocumentProcessingClient()).execute(
        RecordOcrResultCommand(invoice_id=uuid.UUID(invoice_id))
    )

    matched_resp = await client.get(f"/api/v1/invoices/{invoice_id}", headers=CLERK)
    assert matched_resp.json()["status"] == "matched"

    # 5. Same bypass for the outbox-relay-triggered workflow start.
    workflow = await StartApprovalWorkflowUseCase(uow, load_approval_threshold(get_settings())).execute(
        StartApprovalWorkflowCommand(invoice_id=uuid.UUID(invoice_id))
    )
    assert len(workflow.steps) == 1  # $50 total is well under the L1 threshold

    pending_resp = await client.get(f"/api/v1/invoices/{invoice_id}", headers=CLERK)
    assert pending_resp.json()["status"] == "pending_approval"

    # 6. The approver approves the single step via the real API.
    approve_resp = await client.post(f"/api/v1/approvals/{workflow.id}/steps/1/approve", headers=APPROVER)
    assert approve_resp.status_code == 200, approve_resp.text
    assert approve_resp.json()["status"] == "approved"

    approved_invoice = await client.get(f"/api/v1/invoices/{invoice_id}", headers=CLERK)
    assert approved_invoice.json()["status"] == "approved"
    assert approved_invoice.json()["total_amount"] == "50.00"  # 10 units @ $5.00

    # 7. Same bypass for the outbox-relay-triggered payment scheduling.
    await SchedulePaymentUseCase(uow).execute(
        SchedulePaymentCommand(
            invoice_id=uuid.UUID(invoice_id), vendor_id=uuid.UUID(vendor_id), amount_cents=5000
        )
    )

    payments_resp = await client.get("/api/v1/payments", headers=CLERK)
    assert payments_resp.status_code == 200
    scheduled = [p for p in payments_resp.json()["items"] if p["invoice_id"] == invoice_id]
    assert len(scheduled) == 1
    assert scheduled[0]["status"] == "scheduled"
    assert scheduled[0]["amount"] == "50.00"


async def test_mismatched_invoice_surfaces_match_exceptions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await client.get("/api/v1/me", headers=CLERK)

    vendor_resp = await client.post(
        "/api/v1/vendors",
        json={
            "legal_name": "Mismatch Co",
            "contact_email": "ap@mismatch.com",
            "tax_id": "22-2222222",
            "address": {"street": "1 St", "city": "City", "state": "ST", "postal_code": "00000"},
        },
        headers=CLERK,
    )
    vendor_id = vendor_resp.json()["id"]

    po_resp = await client.post(
        "/api/v1/purchase-orders",
        json={
            "vendor_id": vendor_id,
            "line_items": [
                {"line_number": 1, "description": "Gadgets", "quantity": "5", "unit_price": "20.00"}
            ],
        },
        headers=CLERK,
    )
    po_id = po_resp.json()["id"]

    invoice_resp = await client.post(
        "/api/v1/invoices",
        json={
            "invoice_number": "INV-E2E-002",
            "vendor_id": vendor_id,
            "po_id": po_id,
            "line_items": [
                {"line_number": 1, "description": "Gadgets", "quantity": "7", "unit_price": "20.00"}
            ],
        },
        headers=CLERK,
    )
    invoice_id = invoice_resp.json()["id"]

    uow = AppUnitOfWork(db_session)
    await RecordOcrResultUseCase(uow, SimulatedDocumentProcessingClient()).execute(
        RecordOcrResultCommand(invoice_id=uuid.UUID(invoice_id))
    )

    result = await client.get(f"/api/v1/invoices/{invoice_id}", headers=CLERK)
    assert result.json()["status"] == "match_exception"
    assert len(result.json()["match_discrepancies"]) > 0
