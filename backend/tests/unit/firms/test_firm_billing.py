"""Firm plans: what each allows, how a firm upgrades, and how Stripe's events reach the firm."""

import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.api.audit_middleware import AuditEvent
from app.api.rate_limit import limiter
from app.bootstrap.app_factory import create_app
from app.bootstrap.container import get_uow
from app.business.application.commands.handle_stripe_webhook import (
    HandleStripeWebhookCommand,
    HandleStripeWebhookUseCase,
)
from app.business.domain.exceptions import (
    ActiveSubscriptionExistsException,
    DirectPlanChangeNotAllowedException,
    NoStripeCustomerException,
)
from app.config.settings import Settings
from app.firms.application import billing
from app.firms.application.plan_limits import FIRM_PLAN_LIMITS
from app.firms.domain.value_objects import FirmPlan
from app.identity.api.dependencies import get_current_local_user
from app.identity.domain.entities import User
from app.identity.domain.value_objects import EmailAddress
from app.shared.application.ports import StripeEvent
from tests.fakes.fake_ports import FakePasswordHasher, FakePaymentGateway
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

_HASHER = FakePasswordHasher()
LABELS = ("owner", "admin", "extra1", "extra2", "extra3")

BILLING_ON = Settings(
    STRIPE_SECRET_KEY="sk_test_dummy",
    STRIPE_PRICE_ID_FIRM_GROWTH="price_growth",
    STRIPE_PRICE_ID_FIRM_PRACTICE="price_practice",
    STRIPE_PRICE_ID_STARTER="price_starter",
    STRIPE_PRICE_ID_PRO="price_pro",
)
BILLING_OFF = Settings()


class World:
    def __init__(self) -> None:
        self.uow = FakeUnitOfWork()
        self.users: dict[str, User] = {}
        for label in LABELS:
            user = User.register(
                email=EmailAddress(f"{label}@example.com"),
                display_name=label,
                password_hash=_HASHER.hash("pw"),
                verification_token="t",
                verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            self.uow.users.add(user)
            self.users[label] = user


@pytest.fixture
def api() -> Iterator[tuple[World, TestClient]]:
    limiter.enabled = False
    w = World()
    app = create_app()

    async def fake_user(request: Request) -> User:
        return w.users[request.headers["x-test-user"]]

    async def ignore(_: AuditEvent) -> None: ...

    app.dependency_overrides[get_current_local_user] = fake_user
    app.dependency_overrides[get_uow] = lambda: w.uow
    app.state.audit_recorder = ignore
    yield w, TestClient(app, raise_server_exceptions=False)
    limiter.enabled = True


def call(client: TestClient, user: str, method: str, path: str, json: object = None):  # type: ignore[no-untyped-def]
    return client.request(method, f"/api/v1{path}", headers={"x-test-user": user}, json=json)


def new_firm(client: TestClient) -> str:
    return str(call(client, "owner", "POST", "/firms", {"name": "Ledger & Co"}).json()["id"])


# ---------------------------------------------------------------- the limits


def test_a_new_firm_is_on_the_free_plan_and_says_what_it_includes(api: tuple[World, TestClient]) -> None:
    _, client = api
    firm_id = new_firm(client)

    firm = call(client, "owner", "GET", f"/firms/{firm_id}").json()
    summary = call(client, "owner", "GET", f"/firms/{firm_id}/billing").json()

    free = FIRM_PLAN_LIMITS[FirmPlan.FREE]
    assert firm["plan"] == "free"
    assert (summary["max_clients"], summary["max_staff"]) == (free.max_clients, free.max_staff)
    assert (summary["clients"], summary["staff"]) == (0, 1)  # the owner counts as staff


def test_the_free_plan_stops_at_its_client_limit_with_a_clear_reason(api: tuple[World, TestClient]) -> None:
    _, client = api
    firm_id = new_firm(client)
    limit = FIRM_PLAN_LIMITS[FirmPlan.FREE].max_clients
    for i in range(limit):
        assert (
            call(client, "owner", "POST", f"/firms/{firm_id}/clients", {"name": f"Client {i}"}).status_code
            == 201
        )

    over = call(client, "owner", "POST", f"/firms/{firm_id}/clients", {"name": "One too many"})

    assert over.status_code == 409
    assert over.json()["error_code"] == "firm_client_limit_exceeded"
    assert "Upgrade" in over.json()["detail"]


def test_the_free_plan_stops_at_its_staff_limit(api: tuple[World, TestClient]) -> None:
    _, client = api
    firm_id = new_firm(client)

    first = call(
        client, "owner", "POST", f"/firms/{firm_id}/staff", {"email": "admin@example.com", "role": "admin"}
    )
    over = call(
        client, "owner", "POST", f"/firms/{firm_id}/staff", {"email": "extra1@example.com", "role": "viewer"}
    )

    assert first.status_code == 201  # owner + one = 2, the free limit
    assert over.status_code == 409 and over.json()["error_code"] == "firm_staff_limit_exceeded"


def test_upgrading_lifts_the_limits_and_each_plan_allows_more_than_the_last(
    api: tuple[World, TestClient],
) -> None:
    _, client = api
    firm_id = new_firm(client)
    for i in range(FIRM_PLAN_LIMITS[FirmPlan.FREE].max_clients):
        call(client, "owner", "POST", f"/firms/{firm_id}/clients", {"name": f"C{i}"})

    changed = call(client, "owner", "PATCH", f"/firms/{firm_id}/plan", {"plan": "growth"})
    more = call(client, "owner", "POST", f"/firms/{firm_id}/clients", {"name": "Now fits"})

    assert changed.status_code == 200 and changed.json()["plan"] == "growth"
    assert more.status_code == 201
    limits = [FIRM_PLAN_LIMITS[p] for p in (FirmPlan.FREE, FirmPlan.GROWTH, FirmPlan.PRACTICE)]
    assert [x.max_clients for x in limits] == sorted(x.max_clients for x in limits)
    assert [x.max_staff for x in limits] == sorted(x.max_staff for x in limits)


def test_downgrading_never_removes_what_the_firm_already_has(api: tuple[World, TestClient]) -> None:
    _, client = api
    firm_id = new_firm(client)
    call(client, "owner", "PATCH", f"/firms/{firm_id}/plan", {"plan": "growth"})
    ids = [
        call(client, "owner", "POST", f"/firms/{firm_id}/clients", {"name": f"C{i}"}).json()["id"]
        for i in range(4)
    ]

    call(client, "owner", "PATCH", f"/firms/{firm_id}/plan", {"plan": "free"})

    assert len(call(client, "owner", "GET", f"/firms/{firm_id}/clients").json()) == 4  # all still there
    assert call(client, "owner", "GET", f"/businesses/{ids[0]}/sales").status_code == 200
    assert call(client, "owner", "POST", f"/firms/{firm_id}/clients", {"name": "No more"}).status_code == 409


def test_only_the_owner_manages_billing(api: tuple[World, TestClient]) -> None:
    _, client = api
    firm_id = new_firm(client)
    call(client, "owner", "POST", f"/firms/{firm_id}/staff", {"email": "admin@example.com", "role": "admin"})

    assert call(client, "admin", "GET", f"/firms/{firm_id}/billing").status_code == 200  # staff can see usage
    assert call(client, "admin", "PATCH", f"/firms/{firm_id}/plan", {"plan": "practice"}).status_code == 403
    assert (
        call(
            client, "admin", "POST", f"/firms/{firm_id}/billing/checkout-session", {"plan": "growth"}
        ).status_code
        == 403
    )
    assert call(client, "admin", "POST", f"/firms/{firm_id}/billing/portal-session").status_code == 403
    assert (
        call(client, "extra1", "GET", f"/firms/{firm_id}/billing").status_code == 403
    )  # outsiders see nothing


# --------------------------------------------------------------- the payment


async def test_checkout_names_the_firm_and_plan_and_uses_the_firm_price() -> None:
    uow, gateway = FakeUnitOfWork(), FakePaymentGateway()
    firm = await uow.firms.create_firm(name="Ledger", owner_user_id=uuid.uuid4())

    url = await billing.start_checkout(
        uow, gateway, BILLING_ON, firm_id=firm.id, plan=FirmPlan.PRACTICE, actor_email="owner@example.com"
    )

    call_ = gateway.checkout_calls[0]
    assert url.endswith(f"firm:{firm.id}:practice")
    assert (
        call_["price_id"] == "price_practice" and call_["client_reference_id"] == f"firm:{firm.id}:practice"
    )
    assert call_["success_url"].endswith("/app/firm/billing?checkout=success")


async def test_free_cannot_be_checked_out_and_a_subscribed_firm_uses_the_portal() -> None:
    uow, gateway = FakeUnitOfWork(), FakePaymentGateway()
    firm = await uow.firms.create_firm(name="Ledger", owner_user_id=uuid.uuid4())

    with pytest.raises(DirectPlanChangeNotAllowedException):
        await billing.start_checkout(
            uow, gateway, BILLING_ON, firm_id=firm.id, plan=FirmPlan.FREE, actor_email="a@b.co"
        )
    with pytest.raises(NoStripeCustomerException):
        await billing.start_portal(uow, gateway, BILLING_ON, firm_id=firm.id)

    await uow.firms.update_billing(
        firm.id, plan=FirmPlan.GROWTH, stripe_customer_id="cus_1", stripe_subscription_id="sub_1"
    )
    with pytest.raises(ActiveSubscriptionExistsException):
        await billing.start_checkout(
            uow, gateway, BILLING_ON, firm_id=firm.id, plan=FirmPlan.PRACTICE, actor_email="a@b.co"
        )
    assert (await billing.start_portal(uow, gateway, BILLING_ON, firm_id=firm.id)).endswith("cus_1")


async def test_once_billing_is_on_a_paid_plan_cannot_be_set_for_free() -> None:
    uow = FakeUnitOfWork()
    firm = await uow.firms.create_firm(name="Ledger", owner_user_id=uuid.uuid4())

    with pytest.raises(DirectPlanChangeNotAllowedException):
        await billing.set_plan_directly(uow, BILLING_ON, firm_id=firm.id, plan=FirmPlan.PRACTICE)

    await uow.firms.update_billing(firm.id, plan=FirmPlan.GROWTH, stripe_subscription_id="sub_1")
    with pytest.raises(ActiveSubscriptionExistsException):  # cancel in the portal, not here
        await billing.set_plan_directly(uow, BILLING_ON, firm_id=firm.id, plan=FirmPlan.FREE)


async def test_while_billing_is_off_the_owner_can_pick_any_plan() -> None:
    uow = FakeUnitOfWork()
    firm = await uow.firms.create_firm(name="Ledger", owner_user_id=uuid.uuid4())

    updated = await billing.set_plan_directly(uow, BILLING_OFF, firm_id=firm.id, plan=FirmPlan.PRACTICE)

    assert updated.plan == FirmPlan.PRACTICE


# ------------------------------------------------------------ Stripe's events


async def _webhook(uow: FakeUnitOfWork, event: StripeEvent) -> None:
    gateway = FakePaymentGateway()
    gateway.next_event = event
    await HandleStripeWebhookUseCase(uow, gateway, BILLING_ON).execute(
        HandleStripeWebhookCommand(payload=b"{}", signature="sig")
    )


async def test_a_completed_checkout_puts_the_firm_on_the_paid_plan() -> None:
    uow = FakeUnitOfWork()
    firm = await uow.firms.create_firm(name="Ledger", owner_user_id=uuid.uuid4())

    await _webhook(
        uow,
        StripeEvent(
            type="checkout.session.completed",
            data={
                "client_reference_id": f"firm:{firm.id}:growth",
                "customer": "cus_9",
                "subscription": "sub_9",
            },
        ),
    )

    stored = await uow.firms.get_firm(firm.id)
    assert stored is not None
    assert (stored.plan, stored.stripe_customer_id, stored.stripe_subscription_id) == (
        FirmPlan.GROWTH,
        "cus_9",
        "sub_9",
    )


async def test_a_plan_change_in_stripe_moves_the_firm_and_a_cancellation_returns_it_to_free() -> None:
    uow = FakeUnitOfWork()
    firm = await uow.firms.create_firm(name="Ledger", owner_user_id=uuid.uuid4())
    await uow.firms.update_billing(
        firm.id, plan=FirmPlan.GROWTH, stripe_customer_id="cus_9", stripe_subscription_id="sub_9"
    )

    await _webhook(
        uow,
        StripeEvent(
            type="customer.subscription.updated",
            data={"id": "sub_9", "items": {"data": [{"price": {"id": "price_practice"}}]}},
        ),
    )
    assert (await uow.firms.get_firm(firm.id)).plan == FirmPlan.PRACTICE  # type: ignore[union-attr]

    await _webhook(uow, StripeEvent(type="customer.subscription.deleted", data={"id": "sub_9"}))
    ended = await uow.firms.get_firm(firm.id)
    assert ended is not None and ended.plan == FirmPlan.FREE and ended.stripe_subscription_id is None


async def test_an_unknown_price_or_subscription_changes_nothing() -> None:
    uow = FakeUnitOfWork()
    firm = await uow.firms.create_firm(name="Ledger", owner_user_id=uuid.uuid4())
    await uow.firms.update_billing(firm.id, plan=FirmPlan.GROWTH, stripe_subscription_id="sub_9")

    await _webhook(
        uow,
        StripeEvent(
            type="customer.subscription.updated",
            data={"id": "sub_9", "items": {"data": [{"price": {"id": "price_unknown"}}]}},
        ),
    )
    await _webhook(uow, StripeEvent(type="customer.subscription.deleted", data={"id": "sub_other"}))

    assert (await uow.firms.get_firm(firm.id)).plan == FirmPlan.GROWTH  # type: ignore[union-attr]
