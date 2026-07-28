import uuid

from app.approvals.application.commands.start_approval_workflow import (
    StartApprovalWorkflowCommand,
    StartApprovalWorkflowUseCase,
)
from app.approvals.infrastructure.threshold_config import load_approval_threshold
from app.config.settings import get_settings


async def handle_invoice_matched(payload: dict) -> None:
    """Reacts to InvoiceMatched (relayed from the outbox) by starting an
    approval workflow. Opens its own DB transaction, separate from the
    outbox relay's own — event side effects commit independently of the
    outbox bookkeeping write that marks the message published.

    Imports bootstrap.container lazily: this module is pulled in by
    bootstrap/event_handlers.py, which container.py itself imports.
    """
    from app.bootstrap.container import get_container
    from app.bootstrap.unit_of_work import AppUnitOfWork

    container = get_container()
    threshold = load_approval_threshold(get_settings())

    async with container.session_factory() as session:
        uow = AppUnitOfWork(session)
        use_case = StartApprovalWorkflowUseCase(uow, threshold)
        await use_case.execute(StartApprovalWorkflowCommand(invoice_id=uuid.UUID(payload["aggregate_id"])))
