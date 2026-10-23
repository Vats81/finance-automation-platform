"""Personal workspaces: income, budgets and the monthly summary, over HTTP with fakes."""

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
from app.identity.api.dependencies import get_current_local_user
from app.identity.domain.entities import User
from app.identity.domain.value_objects import EmailAddress
from app.personal_finance.domain import rules
from app.shared.domain.exceptions import ValidationException
from tests.fakes.fake_ports import FakePasswordHasher
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

_HASHER = FakePasswordHasher()


class World:
    def __init__(self) -> None:
        self.uow = FakeUnitOfWork()
        self.users: dict[str, User] = {}

    def user(self, label: str) -> None:
        self.users[label] = User.register(
            email=EmailAddress(f"{label}@example.com"),
            display_name=label,
            password_hash=_HASHER.hash("pw"),
            verification_token="t",
            verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        self.uow.users.add(self.users[label])


@pytest.fixture
def api() -> Iterator[tuple[World, TestClient]]:
    limiter.enabled = False
    w = World()
    for label in ("me", "partner", "stranger"):
        w.user(label)
    app = create_app()

    async def fake_user(request: Request) -> User:
        return w.users[request.headers["x-test-user"]]

    async def ignore(_: AuditEvent) -> None: ...

    app.dependency_overrides[get_current_local_user] = fake_user
    app.dependency_overrides[get_uow] = lambda: w.uow
    app.state.audit_recorder = ignore
    yield w, TestClient(app, raise_server_exceptions=False)
    limiter.enabled = True


def call(client: TestClient, user: str, method: str, path: str, json: Any = None) -> Any:
    return client.request(method, f"/api/v1{path}", headers={"x-test-user": user}, json=json)


def personal(client: TestClient, user: str = "me") -> str:
    r = call(client, user, "POST", "/businesses", {"name": "My money", "kind": "personal"})
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def income(
    client: TestClient,
    biz: str,
    amount: str,
    on: str = "2026-10-05",
    source: str = "Salary",
    user: str = "me",
) -> Any:
    return call(
        client,
        user,
        "POST",
        f"/businesses/{biz}/incomes",
        {"income_date": on, "source": source, "category": "Salary", "amount": amount},
    )


def spend(client: TestClient, biz: str, amount: str, category: str, on: str = "2026-10-06") -> Any:
    r = call(
        client,
        "me",
        "POST",
        f"/businesses/{biz}/expenses",
        {
            "expense_date": on,
            "category": category,
            "description": f"{category} spend",
            "amount": amount,
            "payment_method": "card",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def summary(client: TestClient, biz: str, month: int = 10, user: str = "me") -> Any:
    r = call(client, user, "GET", f"/businesses/{biz}/personal/summary?year=2026&month={month}")
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------- rules


def test_month_bounds_handle_leap_years_and_reject_bad_months() -> None:
    assert [str(d) for d in rules.month_bounds(2028, 2)] == ["2028-02-01", "2028-02-29"]
    assert [str(d) for d in rules.month_bounds(2026, 12)] == ["2026-12-01", "2026-12-31"]
    with pytest.raises(ValidationException):
        rules.month_bounds(2026, 13)


def test_budget_status_thresholds() -> None:
    from decimal import Decimal as D

    assert rules.budget_status(D("79"), D("100")) == "ok"
    assert rules.budget_status(D("80"), D("100")) == "near"
    assert rules.budget_status(D("100"), D("100")) == "near"
    assert rules.budget_status(D("100.01"), D("100")) == "over"


# ----------------------------------------------------------------- income


def test_income_belongs_to_personal_workspaces_only(api: tuple[World, TestClient]) -> None:
    _, client = api
    shop = call(client, "me", "POST", "/businesses", {"name": "Shop"}).json()["id"]

    assert income(client, shop, "100").status_code == 422
    assert call(client, "me", "GET", f"/businesses/{shop}/incomes").status_code == 422
    assert call(client, "me", "GET", f"/businesses/{shop}/personal/summary").status_code == 422
    assert (
        call(
            client, "me", "PUT", f"/businesses/{shop}/budgets", {"category": "Food", "monthly_limit": "10"}
        ).status_code
        == 422
    )


def test_recording_and_listing_income(api: tuple[World, TestClient]) -> None:
    _, client = api
    biz = personal(client)

    r = income(client, biz, "2500.00")
    assert r.status_code == 201 and r.json()["amount"] == "2500.00" and r.json()["status"] == "recorded"
    income(client, biz, "300", on="2026-10-20", source="Freelance")
    listed = call(client, "me", "GET", f"/businesses/{biz}/incomes").json()

    assert listed["total"] == 2
    assert [i["source"] for i in listed["items"]] == ["Freelance", "Salary"]  # newest first


@pytest.mark.parametrize("amount", ["0", "-5", "1e15", "abc"])
def test_invalid_income_amounts_are_rejected(api: tuple[World, TestClient], amount: str) -> None:
    _, client = api
    biz = personal(client)

    assert income(client, biz, amount).status_code == 422


def test_income_can_be_voided_once_and_stops_counting(api: tuple[World, TestClient]) -> None:
    _, client = api
    biz = personal(client)
    first = income(client, biz, "1000").json()["id"]
    income(client, biz, "500", source="Gift")

    assert summary(client, biz)["income"] == "1500.00"
    assert call(client, "me", "POST", f"/businesses/{biz}/incomes/{first}/void").status_code == 200
    assert call(client, "me", "POST", f"/businesses/{biz}/incomes/{first}/void").status_code == 422

    assert summary(client, biz)["income"] == "500.00"


def test_income_is_private_to_its_workspace(api: tuple[World, TestClient]) -> None:
    _, client = api
    mine, theirs = personal(client, "me"), personal(client, "stranger")
    secret = income(client, mine, "9999").json()["id"]

    assert call(client, "stranger", "GET", f"/businesses/{mine}/incomes").status_code == 403
    assert call(client, "stranger", "POST", f"/businesses/{theirs}/incomes/{secret}/void").status_code == 404
    assert call(client, "stranger", "GET", f"/businesses/{theirs}/incomes").json()["total"] == 0
    assert call(client, "me", "GET", f"/businesses/{mine}/incomes").json()["total"] == 1


def test_a_viewer_can_look_but_not_change(api: tuple[World, TestClient]) -> None:
    _, client = api
    biz = personal(client)
    assert (
        call(
            client,
            "me",
            "POST",
            f"/businesses/{biz}/team-members",
            {"email": "partner@example.com", "role": "viewer"},
        ).status_code
        == 201
    )

    assert call(client, "partner", "GET", f"/businesses/{biz}/incomes").status_code == 200
    assert call(client, "partner", "GET", f"/businesses/{biz}/personal/summary").status_code == 200
    assert income(client, biz, "5", user="partner").status_code == 403
    assert (
        call(
            client,
            "partner",
            "PUT",
            f"/businesses/{biz}/budgets",
            {"category": "Food", "monthly_limit": "10"},
        ).status_code
        == 403
    )


# ---------------------------------------------------------------- budgets


def test_setting_a_budget_twice_updates_it_ignoring_case(api: tuple[World, TestClient]) -> None:
    _, client = api
    biz = personal(client)

    first = call(
        client, "me", "PUT", f"/businesses/{biz}/budgets", {"category": "Groceries", "monthly_limit": "300"}
    )
    again = call(
        client,
        "me",
        "PUT",
        f"/businesses/{biz}/budgets",
        {"category": "  groceries ", "monthly_limit": "350.50"},
    )

    assert first.status_code == again.status_code == 200
    assert first.json()["id"] == again.json()["id"]
    budgets = call(client, "me", "GET", f"/businesses/{biz}/budgets").json()
    assert [(b["category"], b["monthly_limit"]) for b in budgets] == [("groceries", "350.50")]


@pytest.mark.parametrize("limit", ["0", "-1", "1e15"])
def test_invalid_budget_limits_are_rejected(api: tuple[World, TestClient], limit: str) -> None:
    _, client = api
    biz = personal(client)

    assert (
        call(
            client, "me", "PUT", f"/businesses/{biz}/budgets", {"category": "Food", "monthly_limit": limit}
        ).status_code
        == 422
    )


def test_deleting_a_budget_is_scoped_to_the_workspace(api: tuple[World, TestClient]) -> None:
    _, client = api
    mine, theirs = personal(client, "me"), personal(client, "stranger")
    budget = call(
        client, "me", "PUT", f"/businesses/{mine}/budgets", {"category": "Food", "monthly_limit": "10"}
    ).json()["id"]

    assert call(client, "stranger", "DELETE", f"/businesses/{theirs}/budgets/{budget}").status_code == 404
    assert call(client, "me", "DELETE", f"/businesses/{mine}/budgets/{budget}").status_code == 204
    assert call(client, "me", "DELETE", f"/businesses/{mine}/budgets/{budget}").status_code == 404


# ---------------------------------------------------------------- summary


def test_the_summary_adds_up_income_spending_and_savings(api: tuple[World, TestClient]) -> None:
    _, client = api
    biz = personal(client)
    income(client, biz, "3000")
    spend(client, biz, "900", "Rent")
    spend(client, biz, "300", "Groceries")
    spend(client, biz, "100", "groceries")  # same category, different case
    spend(client, biz, "75.50", "Fun")

    s = summary(client, biz)

    assert (s["income"], s["spending"], s["saved"]) == ("3000.00", "1375.50", "1624.50")
    assert s["savings_rate"] == "0.5415"
    cats = {c["category"]: c for c in s["spending_by_category"]}
    assert [c["category"] for c in s["spending_by_category"]] == ["Rent", "Groceries", "Fun"]
    assert cats["Groceries"]["amount"] == "400.00"
    assert cats["Rent"]["share"] == "0.6543"
    assert (s["period_start"], s["period_end"]) == ("2026-10-01", "2026-10-31")


def test_only_the_chosen_month_counts_and_void_spending_is_ignored(api: tuple[World, TestClient]) -> None:
    _, client = api
    biz = personal(client)
    income(client, biz, "1000", on="2026-10-31")
    income(client, biz, "2000", on="2026-11-01")
    spend(client, biz, "100", "Food", on="2026-10-01")
    spend(client, biz, "999", "Food", on="2026-09-30")
    voided = spend(client, biz, "50", "Food", on="2026-10-10")
    assert (
        call(client, "me", "POST", f"/businesses/{biz}/expenses/{voided['id']}/void", {}).status_code == 200
    )

    october, november = summary(client, biz, 10), summary(client, biz, 11)

    assert (october["income"], october["spending"]) == ("1000.00", "100.00")
    assert (november["income"], november["spending"]) == ("2000.00", "0.00")


def test_savings_rate_is_unknown_without_income_and_negative_when_overspending(
    api: tuple[World, TestClient],
) -> None:
    _, client = api
    biz = personal(client)
    spend(client, biz, "40", "Food")
    no_income = summary(client, biz)
    income(client, biz, "20")
    overspent = summary(client, biz)

    assert no_income["savings_rate"] is None and no_income["saved"] == "-40.00"
    assert overspent["saved"] == "-20.00" and overspent["savings_rate"] == "-1.0000"


def test_budget_progress_marks_ok_near_and_over(api: tuple[World, TestClient]) -> None:
    _, client = api
    biz = personal(client)
    for category, limit, spent in (
        ("Food", "100", "50"),
        ("Fun", "100", "85"),
        ("Transport", "100", "130"),
        ("Unused", "100", "0"),
    ):
        call(
            client, "me", "PUT", f"/businesses/{biz}/budgets", {"category": category, "monthly_limit": limit}
        )
        if spent != "0":
            spend(client, biz, spent, category.upper())  # budget matching ignores case

    progress = {b["category"]: b for b in summary(client, biz)["budgets"]}

    assert progress["Food"]["status"] == "ok" and progress["Food"]["remaining"] == "50.00"
    assert progress["Fun"]["status"] == "near" and progress["Fun"]["percent_used"] == "85.0"
    assert progress["Transport"]["status"] == "over" and progress["Transport"]["remaining"] == "-30.00"
    assert progress["Unused"]["status"] == "ok" and progress["Unused"]["spent"] == "0.00"


def test_the_summary_defaults_to_the_current_month(api: tuple[World, TestClient]) -> None:
    _, client = api
    biz = personal(client)
    now = datetime.now(timezone.utc)

    s = call(client, "me", "GET", f"/businesses/{biz}/personal/summary").json()

    assert s["period_start"] == f"{now.year}-{now.month:02d}-01"


def test_a_new_workspace_can_be_personal_and_defaults_to_business(api: tuple[World, TestClient]) -> None:
    _, client = api

    plain = call(client, "me", "POST", "/businesses", {"name": "Shop"}).json()
    mine = call(client, "me", "POST", "/businesses", {"name": "Me", "kind": "personal"}).json()

    assert (plain["kind"], mine["kind"]) == ("business", "personal")
