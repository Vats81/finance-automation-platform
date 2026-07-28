import uuid

from app.payments.application.commands.schedule_payment import SchedulePaymentCommand, SchedulePaymentUseCase


async def handle_invoice_approved(payload: dict) -> None:
    """Reacts to InvoiceApproved (relayed from the outbox) by scheduling a
    payment. InvoiceApproved already carries vendor_id and
    total_amount_cents, so this handler doesn't need to reload the Invoice.

    Imports bootstrap.container lazily: this module is pulled in by
    bootstrap/event_handlers.py, which container.py itself imports.
    """
    from app.bootstrap.container import get_container
    from app.bootstrap.unit_of_work import AppUnitOfWork

    container = get_container()

    async with container.session_factory() as session:
        uow = AppUnitOfWork(session)
        use_case = SchedulePaymentUseCase(uow)
        await use_case.execute(
            SchedulePaymentCommand(
                invoice_id=uuid.UUID(payload["aggregate_id"]),
                vendor_id=uuid.UUID(payload["vendor_id"]),
                amount_cents=payload["total_amount_cents"],
            )
        )
