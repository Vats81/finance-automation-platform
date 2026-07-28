from app.approvals.application.event_handlers import handle_invoice_matched
from app.audit.application.event_handlers import handle_any_event
from app.identity.application.event_handlers import (
    handle_password_reset_requested,
    handle_user_registered,
)
from app.invoices.application.event_handlers import handle_invoice_submitted
from app.payments.application.event_handlers import handle_invoice_approved
from app.shared.infrastructure.event_bus import InProcessEventBus


def register_all_event_handlers(event_bus: InProcessEventBus) -> None:
    """Composition root for cross-context event subscriptions, called once
    when the shared InProcessEventBus singleton is created (see
    bootstrap/container.py:get_event_bus). Each bounded context that reacts
    to another context's domain events registers its handlers here as it is
    built — e.g. approvals subscribing to InvoiceMatched, payments to
    InvoiceApproved, audit to every event type.
    """
    event_bus.subscribe("InvoiceSubmitted", handle_invoice_submitted)
    event_bus.subscribe("InvoiceMatched", handle_invoice_matched)
    event_bus.subscribe("InvoiceApproved", handle_invoice_approved)
    event_bus.subscribe("UserRegistered", handle_user_registered)
    event_bus.subscribe("PasswordResetRequested", handle_password_reset_requested)
    event_bus.subscribe_to_all(handle_any_event)
