import asyncio

import stripe

from app.shared.application.ports import IPaymentGateway, StripeEvent


class StripeGateway(IPaymentGateway):
    """Real Stripe adapter. The `stripe` SDK is synchronous under the hood
    (blocking HTTP via `requests`), so the two network calls are wrapped in
    `asyncio.to_thread` to avoid blocking the event loop — signature
    verification (`construct_webhook_event`) is pure local HMAC+JSON work,
    fast enough to call directly, same as this codebase's own
    `BcryptPasswordHasher.hash()`/`verify()` (also sync, also called
    directly from async use cases).
    """

    def __init__(self, *, secret_key: str, webhook_secret: str) -> None:
        self._client = stripe.StripeClient(secret_key)
        self._webhook_secret = webhook_secret

    async def create_checkout_session(
        self,
        *,
        customer_id: str | None,
        customer_email: str,
        price_id: str,
        client_reference_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        def _create() -> str:
            params: dict = {
                "mode": "subscription",
                "line_items": [{"price": price_id, "quantity": 1}],
                "client_reference_id": client_reference_id,
                "success_url": success_url,
                "cancel_url": cancel_url,
            }
            if customer_id:
                params["customer"] = customer_id
            else:
                params["customer_email"] = customer_email
            session = self._client.checkout.sessions.create(params)
            return session.url

        return await asyncio.to_thread(_create)

    async def create_billing_portal_session(self, *, customer_id: str, return_url: str) -> str:
        def _create() -> str:
            session = self._client.billing_portal.sessions.create(
                {"customer": customer_id, "return_url": return_url}
            )
            return session.url

        return await asyncio.to_thread(_create)

    def construct_webhook_event(self, *, payload: bytes, signature: str) -> StripeEvent:
        event = stripe.Webhook.construct_event(payload, signature, self._webhook_secret)
        return StripeEvent(type=event["type"], data=event["data"]["object"])
