import uuid

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.rate_limit import limiter
from app.bootstrap.container import get_payment_gateway, get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.api.dependencies import require_business_role
from app.business.api.schemas import (
    BillingPortalSessionResponse,
    CheckoutSessionResponse,
    StartCheckoutSessionRequest,
)
from app.business.application.commands.handle_stripe_webhook import (
    HandleStripeWebhookCommand,
    HandleStripeWebhookUseCase,
)
from app.business.application.commands.start_billing_portal_session import (
    StartBillingPortalSessionCommand,
    StartBillingPortalSessionUseCase,
)
from app.business.application.commands.start_checkout_session import (
    StartCheckoutSessionCommand,
    StartCheckoutSessionUseCase,
)
from app.business.domain.value_objects import BusinessRole
from app.config.settings import get_settings
from app.identity.domain.entities import User
from app.shared.application.ports import IPaymentGateway

router = APIRouter(prefix="/businesses/{business_id}/billing", tags=["billing"])
webhook_router = APIRouter(tags=["billing"])

settings = get_settings()


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
@limiter.limit(settings.rate_limit_write)
async def start_checkout_session(
    request: Request,
    business_id: uuid.UUID,
    body: StartCheckoutSessionRequest,
    actor: User = Depends(require_business_role(BusinessRole.OWNER)),
    uow: AppUnitOfWork = Depends(get_uow),
    payment_gateway: IPaymentGateway = Depends(get_payment_gateway),
) -> CheckoutSessionResponse:
    checkout_url = await StartCheckoutSessionUseCase(uow, payment_gateway, settings).execute(
        StartCheckoutSessionCommand(business_id=business_id, plan=body.plan, actor_email=str(actor.email))
    )
    return CheckoutSessionResponse(checkout_url=checkout_url)


@router.post("/portal-session", response_model=BillingPortalSessionResponse)
@limiter.limit(settings.rate_limit_write)
async def start_billing_portal_session(
    request: Request,
    business_id: uuid.UUID,
    _actor: User = Depends(require_business_role(BusinessRole.OWNER)),
    uow: AppUnitOfWork = Depends(get_uow),
    payment_gateway: IPaymentGateway = Depends(get_payment_gateway),
) -> BillingPortalSessionResponse:
    portal_url = await StartBillingPortalSessionUseCase(uow, payment_gateway, settings).execute(
        StartBillingPortalSessionCommand(business_id=business_id)
    )
    return BillingPortalSessionResponse(portal_url=portal_url)


@webhook_router.post("/billing/webhook", status_code=200, include_in_schema=False)
async def stripe_webhook(
    request: Request,
    uow: AppUnitOfWork = Depends(get_uow),
    payment_gateway: IPaymentGateway = Depends(get_payment_gateway),
) -> dict:
    """Stripe calls this directly — authenticated by signature, not a user
    token, so it's deliberately not behind get_current_local_user or
    require_business_role. Reads the raw body before any Pydantic parsing,
    since the signature covers the exact raw bytes.
    """
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        await HandleStripeWebhookUseCase(uow, payment_gateway, settings).execute(
            HandleStripeWebhookCommand(payload=payload, signature=signature)
        )
    except stripe.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail="Invalid signature") from exc
    return {"received": True}
