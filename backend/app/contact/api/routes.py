from fastapi import APIRouter, Depends, Request

from app.api.rate_limit import limiter
from app.bootstrap.container import get_email_sender
from app.config.settings import get_settings
from app.contact.api.dependencies import get_contact_request_store
from app.contact.api.schemas import ContactReceivedResponse, SubmitContactRequestBody
from app.contact.application.ports import IContactRequestStore
from app.contact.application.submit_contact_request import (
    SubmitContactRequestCommand,
    SubmitContactRequestUseCase,
)
from app.shared.application.ports import IEmailSender

router = APIRouter(prefix="/contact", tags=["contact"])

# Public, unauthenticated endpoint, so noticeably tighter than the general
# write limit. Note this is per client address as slowapi sees it; behind
# a proxy that is only as granular as the forwarded-address handling.
_CONTACT_RATE_LIMIT = "10/hour"


@router.post("", response_model=ContactReceivedResponse, status_code=201)
@limiter.limit(_CONTACT_RATE_LIMIT)
async def submit_contact_request(
    request: Request,
    body: SubmitContactRequestBody,
    store: IContactRequestStore = Depends(get_contact_request_store),
    email_sender: IEmailSender = Depends(get_email_sender),
) -> ContactReceivedResponse:
    if body.website:
        # Honeypot tripped: pretend success so the bot learns nothing.
        return ContactReceivedResponse()

    use_case = SubmitContactRequestUseCase(
        store, email_sender, inbox_email=get_settings().contact_inbox_email
    )
    await use_case.execute(
        SubmitContactRequestCommand(
            name=body.name,
            email=str(body.email),
            business_name=body.business_name or None,
            message=body.message or None,
        )
    )
    return ContactReceivedResponse()
