"""A firm's plan and subscription: what it can add, how it upgrades, how Stripe's events reach it.

Mirrors the per-business billing in app/business, but the subscriber is the firm. The Stripe
checkout reference is "firm:<firm id>:<plan>" so the shared webhook can tell the two apart.
"""

import uuid
from dataclasses import dataclass

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.domain.exceptions import (
    ActiveSubscriptionExistsException,
    DirectPlanChangeNotAllowedException,
    NoStripeCustomerException,
)
from app.config.settings import Settings
from app.firms.application.plan_limits import FIRM_PLAN_LIMITS, FirmPlanLimits
from app.firms.application.ports import FirmRecord
from app.firms.application.use_cases import get_firm_or_404
from app.firms.domain.value_objects import FirmMembershipStatus, FirmPlan
from app.shared.application.ports import IPaymentGateway

FIRM_REFERENCE_PREFIX = "firm:"


def price_ids(settings: Settings) -> dict[FirmPlan, str]:
    return {
        FirmPlan.GROWTH: settings.stripe_price_id_firm_growth,
        FirmPlan.PRACTICE: settings.stripe_price_id_firm_practice,
    }


@dataclass(frozen=True)
class FirmBilling:
    plan: FirmPlan
    limits: FirmPlanLimits
    clients: int
    staff: int
    has_subscription: bool
    stripe_configured: bool


async def billing_summary(uow: AppUnitOfWork, settings: Settings, *, firm_id: uuid.UUID) -> FirmBilling:
    firm = await get_firm_or_404(uow, firm_id)
    clients = await uow.businesses.list_by_firm_id(firm_id)
    members = await uow.firms.list_members(firm_id)
    return FirmBilling(
        plan=firm.plan,
        limits=FIRM_PLAN_LIMITS[firm.plan],
        clients=len(clients),
        staff=sum(1 for m in members if m.status == FirmMembershipStatus.ACTIVE),
        has_subscription=firm.stripe_subscription_id is not None,
        stripe_configured=settings.stripe_configured,
    )


async def start_checkout(
    uow: AppUnitOfWork,
    gateway: IPaymentGateway,
    settings: Settings,
    *,
    firm_id: uuid.UUID,
    plan: FirmPlan,
    actor_email: str,
) -> str:
    firm = await get_firm_or_404(uow, firm_id)
    if plan == FirmPlan.FREE:
        raise DirectPlanChangeNotAllowedException("Nothing to check out for the Free plan")
    if firm.stripe_subscription_id is not None:
        raise ActiveSubscriptionExistsException("Use the billing portal to change your existing plan")
    base_url = settings.frontend_base_url
    return await gateway.create_checkout_session(
        customer_id=firm.stripe_customer_id,
        customer_email=actor_email,
        price_id=price_ids(settings)[plan],
        client_reference_id=f"{FIRM_REFERENCE_PREFIX}{firm.id}:{plan.value}",
        success_url=f"{base_url}/app/firm/billing?checkout=success",
        cancel_url=f"{base_url}/app/firm/billing?checkout=cancelled",
    )


async def start_portal(
    uow: AppUnitOfWork, gateway: IPaymentGateway, settings: Settings, *, firm_id: uuid.UUID
) -> str:
    firm = await get_firm_or_404(uow, firm_id)
    if firm.stripe_customer_id is None:
        raise NoStripeCustomerException("No billing history yet — nothing to manage")
    return await gateway.create_billing_portal_session(
        customer_id=firm.stripe_customer_id,
        return_url=f"{settings.frontend_base_url}/app/firm/billing",
    )


async def set_plan_directly(
    uow: AppUnitOfWork, settings: Settings, *, firm_id: uuid.UUID, plan: FirmPlan
) -> FirmRecord:
    """The unpaid plan flip that exists until Stripe is configured (the beta: no payment is taken),
    exactly like a business's. Once billing is on, paid plans go through checkout and a firm with
    a live subscription must cancel in the portal first.
    """
    firm = await get_firm_or_404(uow, firm_id)
    if settings.stripe_configured:
        if plan != FirmPlan.FREE:
            raise DirectPlanChangeNotAllowedException(
                "Paid plans must be purchased through checkout, not set directly"
            )
        if firm.stripe_subscription_id is not None:
            raise ActiveSubscriptionExistsException("Cancel your subscription in the billing portal first")
    updated = await uow.firms.update_billing(firm_id, plan=plan)
    await uow.commit()
    assert updated is not None
    return updated


# ------------------------------------------------------------- Stripe events


async def on_checkout_completed(
    uow: AppUnitOfWork, *, reference: str, customer_id: str, subscription_id: str
) -> None:
    _, firm_id_str, plan_str = reference.split(":", 2)
    firm = await uow.firms.get_firm(uuid.UUID(firm_id_str))
    if firm is None:
        return
    await uow.firms.update_billing(
        firm.id,
        plan=FirmPlan(plan_str),
        stripe_customer_id=customer_id,
        stripe_subscription_id=subscription_id,
    )
    await uow.commit()


async def on_subscription_updated(
    uow: AppUnitOfWork, settings: Settings, *, subscription_id: str, price_id: str
) -> bool:
    """True if the subscription belongs to a firm (handled here), False if it is not a firm's."""
    firm = await uow.firms.get_firm_by_subscription_id(subscription_id)
    if firm is None:
        return False
    plan = next((p for p, pid in price_ids(settings).items() if pid and pid == price_id), None)
    if plan is not None:
        await uow.firms.update_billing(firm.id, plan=plan, stripe_subscription_id=subscription_id)
        await uow.commit()
    return True


async def on_subscription_deleted(uow: AppUnitOfWork, *, subscription_id: str) -> bool:
    firm = await uow.firms.get_firm_by_subscription_id(subscription_id)
    if firm is None:
        return False
    await uow.firms.update_billing(firm.id, plan=FirmPlan.FREE, clear_subscription=True)
    await uow.commit()
    return True
