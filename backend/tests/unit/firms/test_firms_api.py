"""Accounting firms, end to end over HTTP with in-memory fakes.

The important property: firm staff reach a client business only through their
firm role, only while they are active staff of an active firm, and never reach
anyone else's businesses.
"""

import asyncio
import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi import Request
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.api.audit_middleware import AuditEvent
from app.api.rate_limit import limiter
from app.bootstrap.app_factory import create_app
from app.bootstrap.container import get_uow
from app.firms.domain.value_objects import FirmStatus
from app.identity.api.dependencies import get_current_local_user
from app.identity.domain.entities import User
from app.identity.domain.value_objects import EmailAddress
from tests.fakes.fake_ports import FakePasswordHasher
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

_HASHER = FakePasswordHasher()
STAFF = ("fowner", "fadmin", "faccountant", "fviewer")


class World:
    def __init__(self) -> None:
        self.uow = FakeUnitOfWork()
        self.users: dict[str, User] = {}
        self.audit: list[AuditEvent] = []

    def user(self, label: str) -> User:
        user = User.register(
            email=EmailAddress(f"{label}@example.com"),
            display_name=label,
            password_hash=_HASHER.hash("pw"),
            verification_token="t",
            verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        self.uow.users.add(user)
        self.users[label] = user
        return user


@pytest.fixture
def api() -> Iterator[tuple[World, TestClient]]:
    limiter.enabled = False
    w = World()
    for label in (*STAFF, "client_owner", "stranger", "other_firm_owner"):
        w.user(label)
    app = create_app()

    async def fake_user(request: Request) -> User:
        return w.users[request.headers["x-test-user"]]

    async def record(event: AuditEvent) -> None:
        w.audit.append(event)

    app.dependency_overrides[get_current_local_user] = fake_user
    app.dependency_overrides[get_uow] = lambda: w.uow
    app.state.audit_recorder = record
    yield w, TestClient(app, raise_server_exceptions=False)
    limiter.enabled = True


def call(client: TestClient, user: str, method: str, path: str, json: Any = None) -> Any:
    return client.request(method, f"/api/v1{path}", headers={"x-test-user": user}, json=json)


def build_firm(w: World, client: TestClient) -> tuple[str, dict[str, str]]:
    """A firm with an owner, admin, accountant and viewer. Returns (firm_id, membership ids)."""
    firm_id = call(client, "fowner", "POST", "/firms", {"name": "Ledger & Co"}).json()["id"]
    members: dict[str, str] = {}
    for label, role in (("fadmin", "admin"), ("faccountant", "accountant"), ("fviewer", "viewer")):
        r = call(
            client,
            "fowner",
            "POST",
            f"/firms/{firm_id}/staff",
            {"email": f"{label}@example.com", "role": role},
        )
        assert r.status_code == 201, r.text
        members[label] = r.json()["membership_id"]
    return firm_id, members


def add_client_business(client: TestClient, firm_id: str, name: str = "Bakery Client") -> str:
    r = call(client, "fowner", "POST", f"/firms/{firm_id}/clients", {"name": name})
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ------------------------------------------------------------------ static


def test_every_firm_route_has_a_firm_role_check() -> None:
    app = create_app()
    unguarded = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or "/firms/{firm_id}" not in route.path:
            continue

        def has_check(dep: Any) -> bool:
            return any(hasattr(d.call, "allowed_roles") or has_check(d) for d in dep.dependencies)

        if not has_check(route.dependant):
            unguarded.append(route.path)
    assert unguarded == []


# ------------------------------------------------------------- the firm itself


def test_creating_a_firm_makes_the_creator_its_owner(api: tuple[World, TestClient]) -> None:
    _, client = api

    r = call(client, "fowner", "POST", "/firms", {"name": "Ledger & Co"})

    assert r.status_code == 201
    assert r.json()["my_role"] == "owner" and r.json()["status"] == "active"
    mine = call(client, "fowner", "GET", "/firms").json()
    assert [f["name"] for f in mine] == ["Ledger & Co"]
    assert call(client, "stranger", "GET", "/firms").json() == []


def test_only_staff_can_see_a_firm(api: tuple[World, TestClient]) -> None:
    w, client = api
    firm_id, _ = build_firm(w, client)

    for path in ("", "/staff", "/clients"):
        assert call(client, "stranger", "GET", f"/firms/{firm_id}{path}").status_code == 403
        for staff in STAFF:
            assert call(client, staff, "GET", f"/firms/{firm_id}{path}").status_code == 200


def test_staff_management_follows_the_policy(api: tuple[World, TestClient]) -> None:
    w, client = api
    firm_id, m = build_firm(w, client)
    base = f"/firms/{firm_id}/staff"

    # accountants and viewers cannot manage staff or add clients
    for who in ("faccountant", "fviewer"):
        assert (
            call(client, who, "POST", base, {"email": "stranger@example.com", "role": "viewer"}).status_code
            == 403
        )
        assert call(client, who, "PATCH", f"{base}/{m['fviewer']}", {"role": "admin"}).status_code == 403
        assert call(client, who, "POST", f"/firms/{firm_id}/clients", {"name": "X"}).status_code == 403
    # an admin can
    assert (
        call(client, "fadmin", "POST", base, {"email": "stranger@example.com", "role": "viewer"}).status_code
        == 201
    )


def test_the_owner_role_is_never_granted_and_the_owner_is_untouchable(api: tuple[World, TestClient]) -> None:
    w, client = api
    firm_id, m = build_firm(w, client)
    base = f"/firms/{firm_id}/staff"
    owner_membership = next(
        s["membership_id"] for s in call(client, "fowner", "GET", base).json() if s["role"] == "owner"
    )

    assert (
        call(client, "fadmin", "POST", base, {"email": "stranger@example.com", "role": "owner"}).status_code
        == 422
    )
    assert call(client, "fadmin", "PATCH", f"{base}/{m['fviewer']}", {"role": "owner"}).status_code == 422
    assert (
        call(client, "fadmin", "PATCH", f"{base}/{owner_membership}", {"role": "viewer"}).status_code == 422
    )
    assert call(client, "fadmin", "POST", f"{base}/{owner_membership}/remove").status_code == 422
    assert call(client, "fowner", "POST", f"{base}/{owner_membership}/remove").status_code == 422
    assert (
        call(client, "fadmin", "PATCH", f"{base}/{m['fadmin']}", {"role": "viewer"}).status_code == 422
    )  # own role


def test_inviting_requires_a_registered_user_and_rejects_duplicates(api: tuple[World, TestClient]) -> None:
    w, client = api
    firm_id, _ = build_firm(w, client)
    base = f"/firms/{firm_id}/staff"

    assert (
        call(client, "fowner", "POST", base, {"email": "nobody@example.com", "role": "viewer"}).status_code
        == 422
    )
    assert (
        call(client, "fowner", "POST", base, {"email": "fviewer@example.com", "role": "viewer"}).status_code
        == 409
    )


def test_a_staff_membership_from_another_firm_is_not_actionable(api: tuple[World, TestClient]) -> None:
    w, client = api
    firm_id, _ = build_firm(w, client)
    other_firm = call(client, "other_firm_owner", "POST", "/firms", {"name": "Rival LLP"}).json()["id"]
    other_member = call(client, "other_firm_owner", "GET", f"/firms/{other_firm}/staff").json()[0][
        "membership_id"
    ]

    assert (
        call(
            client, "fowner", "PATCH", f"/firms/{firm_id}/staff/{other_member}", {"role": "viewer"}
        ).status_code
        == 404
    )
    assert call(client, "fowner", "POST", f"/firms/{firm_id}/staff/{other_member}/remove").status_code == 404


# ------------------------------------------------- reaching client businesses


def test_staff_reach_a_client_business_with_the_role_their_firm_role_maps_to(
    api: tuple[World, TestClient],
) -> None:
    w, client = api
    firm_id, _ = build_firm(w, client)
    biz = add_client_business(client, firm_id)

    def status(user: str, method: str, path: str, body: Any = None) -> int:
        return int(call(client, user, method, f"/businesses/{biz}{path}", body).status_code)

    for staff in STAFF:  # everyone on staff can read
        assert status(staff, "GET", "/sales") == 200
        assert status(staff, "GET", "/dashboard/summary") == 200
    # writes: owner/admin/accountant yes, viewer no
    for staff, allowed in (("fowner", True), ("fadmin", True), ("faccountant", True), ("fviewer", False)):
        code = status(staff, "POST", "/expenses", {})
        assert (code != 403) is allowed, (staff, code)
    # team management: owner/admin yes, accountant/viewer no
    for staff, allowed in (("fadmin", True), ("faccountant", False), ("fviewer", False)):
        code = status(staff, "POST", "/team-members", {})
        assert (code != 403) is allowed, (staff, code)
    # the plan is the business owner's, never a firm admin's; fowner holds it as the creator
    assert status("fadmin", "PATCH", "/plan", {"plan": "pro"}) == 403
    assert status("fowner", "PATCH", "/plan", {"plan": "pro"}) == 200


def test_people_outside_the_firm_get_nothing(api: tuple[World, TestClient]) -> None:
    w, client = api
    firm_id, _ = build_firm(w, client)
    biz = add_client_business(client, firm_id)
    call(client, "other_firm_owner", "POST", "/firms", {"name": "Rival LLP"})

    for who in ("stranger", "client_owner", "other_firm_owner"):
        assert call(client, who, "GET", f"/businesses/{biz}/sales").status_code == 403
        assert call(client, who, "GET", f"/businesses/{biz}").status_code == 403


def test_removing_staff_cuts_off_their_client_access_on_the_next_request(
    api: tuple[World, TestClient],
) -> None:
    w, client = api
    firm_id, m = build_firm(w, client)
    biz = add_client_business(client, firm_id)
    assert call(client, "faccountant", "GET", f"/businesses/{biz}/sales").status_code == 200

    removed = call(client, "fowner", "POST", f"/firms/{firm_id}/staff/{m['faccountant']}/remove")
    assert removed.status_code == 200

    assert call(client, "faccountant", "GET", f"/businesses/{biz}/sales").status_code == 403
    assert call(client, "faccountant", "GET", f"/firms/{firm_id}").status_code == 403


def test_a_role_change_applies_to_client_access_immediately(api: tuple[World, TestClient]) -> None:
    w, client = api
    firm_id, m = build_firm(w, client)
    biz = add_client_business(client, firm_id)
    assert call(client, "faccountant", "POST", f"/businesses/{biz}/expenses", {}).status_code != 403

    call(client, "fowner", "PATCH", f"/firms/{firm_id}/staff/{m['faccountant']}", {"role": "viewer"})

    assert call(client, "faccountant", "POST", f"/businesses/{biz}/expenses", {}).status_code == 403
    assert call(client, "faccountant", "GET", f"/businesses/{biz}/expenses").status_code == 200


def test_a_suspended_firm_loses_access_to_its_clients(api: tuple[World, TestClient]) -> None:
    w, client = api
    firm_id, _ = build_firm(w, client)
    biz = add_client_business(client, firm_id)
    firm = w.uow.firms.firms[uuid.UUID(firm_id)]
    w.uow.firms.firms[firm.id] = type(firm)(**{**firm.__dict__, "status": FirmStatus.SUSPENDED})

    assert call(client, "fadmin", "GET", f"/businesses/{biz}/sales").status_code == 403
    assert call(client, "fadmin", "GET", f"/firms/{firm_id}/clients").status_code == 403


def test_a_firm_cannot_see_into_another_firms_clients(api: tuple[World, TestClient]) -> None:
    w, client = api
    firm_id, _ = build_firm(w, client)
    other_firm = call(client, "other_firm_owner", "POST", "/firms", {"name": "Rival LLP"}).json()["id"]
    rival_client = call(
        client, "other_firm_owner", "POST", f"/firms/{other_firm}/clients", {"name": "Rival Client"}
    ).json()["id"]

    assert call(client, "fowner", "GET", f"/businesses/{rival_client}/sales").status_code == 403
    assert call(client, "fowner", "GET", f"/firms/{other_firm}/clients").status_code == 403
    assert [
        c["business"]["name"] for c in call(client, "fowner", "GET", f"/firms/{firm_id}/clients").json()
    ] == []


def test_a_user_in_two_places_gets_the_stronger_role(api: tuple[World, TestClient]) -> None:
    w, client = api
    firm_id, _ = build_firm(w, client)
    biz = add_client_business(client, firm_id)
    # the firm viewer is also invited directly as the client's accountant
    r = call(
        client,
        "fowner",
        "POST",
        f"/businesses/{biz}/team-members",
        {"email": "fviewer@example.com", "role": "accountant"},
    )
    assert r.status_code == 201, r.text

    assert call(client, "fviewer", "POST", f"/businesses/{biz}/expenses", {}).status_code != 403


def test_firm_work_is_audited_with_the_firm_role(api: tuple[World, TestClient]) -> None:
    w, client = api
    firm_id, _ = build_firm(w, client)
    biz = add_client_business(client, firm_id)
    w.audit.clear()

    call(client, "fadmin", "POST", f"/businesses/{biz}/customers", {"name": "Acme"})

    assert [e.actor_role for e in w.audit] == ["firm_admin"]


def test_the_business_switcher_lists_client_businesses_marked_as_via_firm(
    api: tuple[World, TestClient],
) -> None:
    w, client = api
    firm_id, _ = build_firm(w, client)
    biz = add_client_business(client, firm_id)

    mine = call(client, "faccountant", "GET", "/businesses").json()

    entry = next(b for b in mine if b["business"]["id"] == biz)
    assert entry["via_firm"] is True and entry["role"] == "accountant" and entry["firm_name"] == "Ledger & Co"
    assert call(client, "stranger", "GET", "/businesses").json() == []


# ------------------------------------------------------------- client overview


def test_the_client_overview_lists_every_client_with_headline_numbers(api: tuple[World, TestClient]) -> None:
    w, client = api
    firm_id, _ = build_firm(w, client)
    first = add_client_business(client, firm_id, "Bakery Client")
    add_client_business(client, firm_id, "Cafe Client")
    call(
        client,
        "fowner",
        "POST",
        f"/businesses/{first}/expenses",
        {
            "expense_date": "2026-10-02",
            "category": "Rent",
            "description": "r",
            "amount": "50",
            "payment_method": "cash",
        },
    )

    rows = call(client, "fviewer", "GET", f"/firms/{firm_id}/clients").json()

    assert [r["business"]["name"] for r in rows] == ["Bakery Client", "Cafe Client"]
    bakery = rows[0]
    assert bakery["total_expenses"] == "50.00" and bakery["net_profit"] == "-50.00"
    assert rows[1]["total_expenses"] == "0.00"


# -------------------------------------------------------------------- release


def test_releasing_a_client_needs_someone_on_the_clients_side(api: tuple[World, TestClient]) -> None:
    w, client = api
    firm_id, _ = build_firm(w, client)
    biz = add_client_business(client, firm_id)
    release = f"/firms/{firm_id}/clients/{biz}/release"

    # only the firm's own people can run it today -> refused
    assert call(client, "fowner", "POST", release).status_code == 409

    # the client's owner is given access (needs an account), then it can leave
    assert (
        call(
            client,
            "fowner",
            "POST",
            f"/businesses/{biz}/team-members",
            {"email": "client_owner@example.com", "role": "admin"},
        ).status_code
        == 201
    )
    assert call(client, "faccountant", "POST", release).status_code == 403  # not allowed to release
    assert call(client, "fowner", "POST", release).status_code == 200

    # the firm's staff lose access; the client keeps theirs
    assert call(client, "fadmin", "GET", f"/businesses/{biz}/sales").status_code == 403
    assert call(client, "client_owner", "GET", f"/businesses/{biz}/sales").status_code == 200
    assert call(client, "fowner", "GET", f"/firms/{firm_id}/clients").json() == []


def test_a_client_of_another_firm_cannot_be_released(api: tuple[World, TestClient]) -> None:
    w, client = api
    firm_id, _ = build_firm(w, client)
    other_firm = call(client, "other_firm_owner", "POST", "/firms", {"name": "Rival LLP"}).json()["id"]
    rival_client = call(
        client, "other_firm_owner", "POST", f"/firms/{other_firm}/clients", {"name": "Rival Client"}
    ).json()["id"]

    assert (
        call(client, "fowner", "POST", f"/firms/{firm_id}/clients/{rival_client}/release").status_code == 404
    )


def test_an_ordinary_business_is_unaffected(api: tuple[World, TestClient]) -> None:
    w, client = api
    own = call(client, "stranger", "POST", "/businesses", {"name": "Solo Shop"}).json()["id"]

    assert call(client, "stranger", "GET", f"/businesses/{own}/sales").status_code == 200
    assert call(client, "fowner", "GET", f"/businesses/{own}/sales").status_code == 403
    assert call(client, "stranger", "GET", f"/businesses/{own}").json()["firm_id"] is None


def test_new_workspaces_can_be_personal(api: tuple[World, TestClient]) -> None:
    w, client = api

    r = call(client, "stranger", "POST", "/businesses", {"name": "My money", "kind": "personal"})

    assert r.status_code == 201 and r.json()["kind"] == "personal"
    assert (
        call(client, "stranger", "POST", "/businesses", {"name": "Nope", "kind": "bogus"}).status_code == 422
    )


def _run(coro: Any) -> Any:
    return asyncio.run(coro)
