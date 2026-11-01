import uuid
from dataclasses import dataclass

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.domain.value_objects import BusinessPlan
from app.config.settings import Settings
from app.firms.application import billing as firm_billing
from app.shared.application.ports import IPaymentGateway


@dataclass(frozen=True)
class HandleStripeWebhookCommand:
    payload: bytes
    signature: str


class HandleStripeWebhookUseCase:
    """Verifies and dispatches a Stripe webhook. Any event type this
    doesn't recognize is a deliberate no-op, not an error — Stripe expects
    a 2xx for events we don't act on, or it retries forever.

    Idempotency is accepted-as-is rather than tracked with a processed-
    event-id table: every branch here calls into a naturally idempotent
    domain method (change_plan no-ops if unchanged, re-attaching the same
    subscription id twice is harmless), which is enough for a first cut —
    worth revisiting only if double-delivery ever actually causes a
    problem.
    """

    def __init__(self, uow: AppUnitOfWork, payment_gateway: IPaymentGateway, settings: Settings) -> None:
        self._uow = uow
        self._payment_gateway = payment_gateway
        self._settings = settings

    async def execute(self, command: HandleStripeWebhookCommand) -> None:
        event = self._payment_gateway.construct_webhook_event(
            payload=command.payload, signature=command.signature
        )

        if event.type == "checkout.session.completed":
            reference = event.data["client_reference_id"]
            if reference.startswith(firm_billing.FIRM_REFERENCE_PREFIX):
                await firm_billing.on_checkout_completed(
                    self._uow,
                    reference=reference,
                    customer_id=event.data["customer"],
                    subscription_id=event.data["subscription"],
                )
                return
            business_id_str, plan_str = reference.split(":", 1)
            business = await self._uow.businesses.get_by_id(uuid.UUID(business_id_str))
            if business is None:
                return
            business.attach_stripe_customer(customer_id=event.data["customer"])
            business.activate_subscription(
                subscription_id=event.data["subscription"], plan=BusinessPlan(plan_str)
            )
            await self._uow.businesses.update(business)
            await self._uow.commit()

        elif event.type == "customer.subscription.updated":
            business = await self._uow.businesses.get_by_stripe_subscription_id(event.data["id"])
            if business is None:
                await firm_billing.on_subscription_updated(
                    self._uow,
                    self._settings,
                    subscription_id=event.data["id"],
                    price_id=event.data["items"]["data"][0]["price"]["id"],
                )
                return
            price_id = event.data["items"]["data"][0]["price"]["id"]
            plan = self._resolve_plan_from_price_id(price_id)
            if plan is None:
                return
            business.activate_subscription(subscription_id=event.data["id"], plan=plan)
            await self._uow.businesses.update(business)
            await self._uow.commit()

        elif event.type == "customer.subscription.deleted":
            business = await self._uow.businesses.get_by_stripe_subscription_id(event.data["id"])
            if business is None:
                await firm_billing.on_subscription_deleted(self._uow, subscription_id=event.data["id"])
                return
            business.cancel_subscription()
            await self._uow.businesses.update(business)
            await self._uow.commit()

        # else: an event type we don't act on — no-op.

    def _resolve_plan_from_price_id(self, price_id: str) -> BusinessPlan | None:
        mapping = {
            self._settings.stripe_price_id_starter: BusinessPlan.STARTER,
            self._settings.stripe_price_id_pro: BusinessPlan.PRO,
            # The personal paid plan ("Plus") is the Starter tier of a personal workspace.
            self._settings.stripe_price_id_personal: BusinessPlan.STARTER,
        }
        mapping.pop("", None)  # a price that is not configured must never match
        return mapping.get(price_id)
