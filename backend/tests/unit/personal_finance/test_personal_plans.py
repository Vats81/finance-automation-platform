"""What a personal account includes for free, and what Plus adds."""

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from typing import Any

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
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.application.commands.start_checkout_session import (
    StartCheckoutSessionCommand,
    StartCheckoutSessionUseCase,
)
from app.business.domain.value_objects import BusinessKind, BusinessPlan
from app.config.settings import Settings
from app.identity.api.dependencies import get_current_local_user
from app.identity.domain.entities import User
from app.identity.domain.value_objects import EmailAddress
from app.personal_finance.domain.rules import FREE_MAX_BUDGETS
from app.shared.application.ports import StripeEvent
from app.shared.domain.exceptions import ValidationException
from tests.fakes.fake_ports import FakePasswordHasher, FakePaymentGateway
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

_HASHER = FakePasswordHasher()
SETTINGS = Settings(
    STRIPE_SECRET_KEY="sk_test_dummy",
    STRIPE_PRICE_ID_STARTER="price_business_starter",
    STRIPE_PRICE_ID_PRO="price_business_pro",
    STRIPE_PRICE_ID_PERSONAL="price_personal_plus",
)


@pytest.fixture
def api() -> Iterator[tuple[FakeUnitOfWork, TestClient]]:
    limiter.enabled = False
    uow = FakeUnitOfWork()
    users: dict[str, User] = {}
    for label in ("me", "partner"):
        user = User.register(
            email=EmailAddress(f"{label}@example.com"),
            display_name=label,
            password_hash=_HASHER.hash("pw"),
            verification_token="t",
            verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        uow.users.add(user)
        users[label] = user
    app = create_app()

    async def fake_user(request: Request) -> User:
        return users[request.headers["x-test-user"]]

    async def ignore(_: AuditEvent) -> None: ...

    app.dependency_overrides[get_current_local_user] = fake_user
    app.dependency_overrides[get_uow] = lambda: uow
    app.state.audit_recorder = ignore
    yield uow, TestClient(app, raise_server_exceptions=False)
    limiter.enabled = True


def call(client: TestClient, path: str, method: str = "GET", json: Any = None, user: str = "me") -> Any:
    return client.request(method, f"/api/v1{path}", headers={"x-test-user": user}, json=json)


def workspace(client: TestClient) -> str:
    return str(call(client, "/businesses", "POST", {"name": "My money", "kind": "personal"}).json()["id"])


def set_budget(client: TestClient, biz: str, category: str, limit: str = "100") -> Any:
    return call(client, f"/businesses/{biz}/budgets", "PUT", {"category": category, "monthly_limit": limit})


# ------------------------------------------------------- one per person


def test_a_person_has_one_personal_workspace(api: tuple[FakeUnitOfWork, TestClient]) -> None:
    _, client = api
    first = call(client, "/businesses", "POST", {"name": "Mine", "kind": "personal"})
    second = call(client, "/businesses", "POST", {"name": "Mine again", "kind": "personal"})
    other = call(client, "/businesses", "POST", {"name": "Partner's", "kind": "personal"}, user="partner")

    assert first.status_code == 201 and other.status_code == 201
    assert second.status_code == 409 and second.json()["error_code"] == "personal_workspace_exists"


def test_having_a_personal_workspace_does_not_stop_you_owning_businesses(
    api: tuple[FakeUnitOfWork, TestClient],
) -> None:
    _, client = api
    workspace(client)

    assert call(client, "/businesses", "POST", {"name": "Shop"}).status_code == 201
    assert call(client, "/businesses", "POST", {"name": "Second shop"}).status_code == 201


# -------------------------------------------------- the free budget limit


def test_the_free_plan_allows_a_limited_number_of_budgets(api: tuple[FakeUnitOfWork, TestClient]) -> None:
    _, client = api
    biz = workspace(client)
    for i in range(FREE_MAX_BUDGETS):
        assert set_budget(client, biz, f"Category {i}").status_code == 200

    over = set_budget(client, biz, "One more")

    assert over.status_code == 409 and over.json()["error_code"] == "personal_plan_limit_reached"
    assert "Plus" in over.json()["detail"]


def test_changing_an_existing_budget_is_not_blocked_at_the_limit(
    api: tuple[FakeUnitOfWork, TestClient],
) -> None:
    _, client = api
    biz = workspace(client)
    for i in range(FREE_MAX_BUDGETS):
        set_budget(client, biz, f"Category {i}")

    assert set_budget(client, biz, "category 0", "999").status_code == 200  # same budget, any capitals
    assert len(call(client, f"/businesses/{biz}/budgets").json()) == FREE_MAX_BUDGETS


def test_removing_a_budget_makes_room_and_plus_has_no_limit(api: tuple[FakeUnitOfWork, TestClient]) -> None:
    uow, client = api
    biz = workspace(client)
    ids = [set_budget(client, biz, f"Category {i}").json()["id"] for i in range(FREE_MAX_BUDGETS)]

    call(client, f"/businesses/{biz}/budgets/{ids[0]}", "DELETE")
    assert set_budget(client, biz, "Fits now").status_code == 200
    assert set_budget(client, biz, "Over again").status_code == 409

    import asyncio
    import uuid

    business = asyncio.run(uow.businesses.get_by_id(uuid.UUID(biz)))
    assert business is not None
    business.change_plan(plan=BusinessPlan.STARTER)
    assert set_budget(client, biz, "Plus has room").status_code == 200


# --------------------------------------------------------------- paying


async def test_plus_is_checked_out_at_the_personal_price() -> None:
    uow, gateway = FakeUnitOfWork(), FakePaymentGateway()
    import uuid

    owner = uuid.uuid4()
    mine = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=owner, name="Me", kind=BusinessKind.PERSONAL)
    )
    shop = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=owner, name="Shop")
    )
    use_case = StartCheckoutSessionUseCase(uow, gateway, SETTINGS)

    await use_case.execute(
        StartCheckoutSessionCommand(business_id=mine.id, plan=BusinessPlan.STARTER, actor_email="a@b.co")
    )
    await use_case.execute(
        StartCheckoutSessionCommand(business_id=shop.id, plan=BusinessPlan.STARTER, actor_email="a@b.co")
    )

    assert [c["price_id"] for c in gateway.checkout_calls] == [
        "price_personal_plus",
        "price_business_starter",
    ]


async def test_a_personal_account_has_only_one_paid_plan() -> None:
    import uuid

    uow, gateway = FakeUnitOfWork(), FakePaymentGateway()
    mine = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Me", kind=BusinessKind.PERSONAL)
    )

    with pytest.raises(ValidationException):
        await StartCheckoutSessionUseCase(uow, gateway, SETTINGS).execute(
            StartCheckoutSessionCommand(business_id=mine.id, plan=BusinessPlan.PRO, actor_email="a@b.co")
        )


async def test_stripe_moving_a_personal_subscription_to_the_plus_price_keeps_it_on_plus() -> None:
    import uuid

    uow, gateway = FakeUnitOfWork(), FakePaymentGateway()
    mine = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Me", kind=BusinessKind.PERSONAL)
    )
    mine.attach_stripe_customer(customer_id="cus_1")
    mine.activate_subscription(subscription_id="sub_1", plan=BusinessPlan.STARTER)
    gateway.next_event = StripeEvent(
        type="customer.subscription.updated",
        data={"id": "sub_1", "items": {"data": [{"price": {"id": "price_personal_plus"}}]}},
    )

    await HandleStripeWebhookUseCase(uow, gateway, SETTINGS).execute(
        HandleStripeWebhookCommand(payload=b"{}", signature="sig")
    )

    stored = await uow.businesses.get_by_id(mine.id)
    assert stored is not None and stored.plan == BusinessPlan.STARTER
