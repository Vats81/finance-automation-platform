"""Beta RBAC / tenant-isolation matrix, enforced at the HTTP boundary.

Two layers:
1. A static audit of every business-scoped route: each must carry a role check
   (deny by default), and the roles must match the policy in
   app/business/api/permissions.py. A new route that forgets the check, or
   quietly lets viewers write, fails here.
2. Behavioural tests that drive the real app with in-memory fakes and check
   what each role actually gets back (403 vs not-403), including suspension,
   removal taking effect on the next request, and cross-tenant ids.
"""

import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest
from fastapi import Request
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.api.audit_middleware import AuditEvent, describe
from app.api.rate_limit import limiter
from app.bootstrap.app_factory import create_app
from app.bootstrap.container import get_uow
from app.business.api.permissions import (
    ANY_MEMBER,
    CAN_EDIT_SETTINGS,
    CAN_EXPORT,
    CAN_MANAGE_TEAM,
    CAN_WRITE,
    OWNER_ONLY,
)
from app.business.application.commands.invite_team_member import (
    InviteTeamMemberCommand,
    InviteTeamMemberUseCase,
)
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.domain.value_objects import BusinessPlan, BusinessRole, BusinessStatus
from app.identity.api.dependencies import get_current_local_user
from app.identity.domain.entities import User
from app.identity.domain.value_objects import EmailAddress
from tests.fakes.fake_ports import FakeEmailSender, FakePasswordHasher
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

# ---------------------------------------------------------------- static audit

_EXPECTED_OVERRIDES: dict[tuple[str, str], tuple[BusinessRole, ...]] = {
    ("GET", "/businesses/{business_id}/dashboard/profit-loss-pdf"): CAN_EXPORT,
    ("GET", "/businesses/{business_id}/imports/jobs/{job_id}"): CAN_WRITE,
    ("GET", "/businesses/{business_id}/audit-events"): CAN_MANAGE_TEAM,
    ("PATCH", "/businesses/{business_id}/onboarding"): CAN_EDIT_SETTINGS,
    ("PATCH", "/businesses/{business_id}/plan"): OWNER_ONLY,
    ("POST", "/businesses/{business_id}/billing/checkout-session"): OWNER_ONLY,
    ("POST", "/businesses/{business_id}/billing/portal-session"): OWNER_ONLY,
    # The assistant only has read-only tools (see test_ai_tools_are_read_only),
    # so a viewer may ask it questions.
    ("POST", "/businesses/{business_id}/ai-assistant/ask"): ANY_MEMBER,
    # Downloading an empty header-only template is harmless.
    ("GET", "/businesses/{business_id}/imports/{data_type}/template"): ANY_MEMBER,
}
_TEAM_PREFIX = "/businesses/{business_id}/team-members"


def _roles_of(dependant: Any) -> tuple[BusinessRole, ...] | None:
    for dep in dependant.dependencies:
        if hasattr(dep.call, "allowed_roles"):
            return tuple(dep.call.allowed_roles)
        nested = _roles_of(dep)
        if nested is not None:
            return nested
    return None


def _business_routes() -> list[tuple[str, str, tuple[BusinessRole, ...] | None]]:
    app = create_app()
    rows = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        path = route.path.removeprefix("/api/v1")
        # /admin/* is gated by require_platform_admin, a separate mechanism.
        # /admin/* is platform-admin gated and /firms/* is firm-role gated (see tests/unit/firms);
        # both are separate mechanisms from the per-business role check audited here.
        if "{business_id}" not in path or path.startswith(("/admin/", "/firms/")):
            continue
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            rows.append((method, path, _roles_of(route.dependant)))
    return rows


def _expected(method: str, path: str) -> tuple[BusinessRole, ...]:
    if (method, path) in _EXPECTED_OVERRIDES:
        return _EXPECTED_OVERRIDES[(method, path)]
    if path.startswith(_TEAM_PREFIX) and method != "GET":
        return CAN_MANAGE_TEAM
    return ANY_MEMBER if method == "GET" else CAN_WRITE


_ROUTES = _business_routes()


def test_there_are_business_routes_to_audit() -> None:
    assert len(_ROUTES) > 50


@pytest.mark.parametrize(("method", "path", "roles"), _ROUTES, ids=[f"{m} {p}" for m, p, _ in _ROUTES])
def test_every_business_route_enforces_exactly_the_policy_roles(
    method: str, path: str, roles: tuple[BusinessRole, ...] | None
) -> None:
    assert roles is not None, f"{method} {path} has no business role check (deny by default)"
    assert set(roles) == set(_expected(method, path)), f"{method} {path}: unexpected roles {roles}"


def test_legacy_unscoped_ap_apis_are_not_mounted() -> None:
    # /vendors, /invoices, /payments, /purchase-orders, /approvals, /audit-log
    # are the old AP product's endpoints: not business-scoped and (for local
    # logins) they only ever returned 500. They must not be reachable.
    paths = {r.path.removeprefix("/api/v1") for r in create_app().routes if isinstance(r, APIRoute)}
    for legacy in ("/vendors", "/invoices", "/payments", "/purchase-orders", "/approvals"):
        assert not any(p == legacy or p.startswith(legacy + "/") for p in paths), legacy


def test_ai_tools_are_read_only() -> None:
    from app.ai_assistant.application.tools import TOOL_SCHEMAS

    names = [schema["name"] for schema in TOOL_SCHEMAS]
    assert names, "no tools registered"
    assert all(n.startswith(("get_", "list_")) for n in names), names


# ---------------------------------------------------------------- behavioural

_PASSWORD_HASHER = FakePasswordHasher()


class World:
    def __init__(self) -> None:
        self.uow = FakeUnitOfWork()
        self.users: dict[str, User] = {}
        self.business_a = uuid.UUID(int=0)
        self.business_b = uuid.UUID(int=0)
        self.members: dict[str, uuid.UUID] = {}  # role -> membership id (business A)
        self.audit: list[AuditEvent] = []

    def add_user(self, label: str) -> User:
        user = User.register(
            email=EmailAddress(f"{label}@example.com"),
            display_name=label,
            password_hash=_PASSWORD_HASHER.hash("pw"),
            verification_token="tok",
            verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        self.uow.users.add(user)
        self.users[label] = user
        return user


@pytest.fixture
def world() -> Iterator[tuple[World, TestClient]]:
    limiter.enabled = False
    w = World()
    owner_a, owner_b = w.add_user("owner_a"), w.add_user("owner_b")
    for label in ("admin", "accountant", "viewer", "outsider"):
        w.add_user(label)

    import asyncio

    async def build() -> None:
        biz_a = await RegisterBusinessUseCase(w.uow).execute(
            RegisterBusinessCommand(owner_user_id=owner_a.id, name="Biz A")
        )
        biz_b = await RegisterBusinessUseCase(w.uow).execute(
            RegisterBusinessCommand(owner_user_id=owner_b.id, name="Biz B")
        )
        w.business_a, w.business_b = biz_a.id, biz_b.id
        # The free plan caps the team at 2; the matrix needs four roles.
        biz_a.plan = BusinessPlan.PRO
        await w.uow.businesses.update(biz_a)
        for label, role in (
            ("admin", BusinessRole.ADMIN),
            ("accountant", BusinessRole.ACCOUNTANT),
            ("viewer", BusinessRole.VIEWER),
        ):
            m = await InviteTeamMemberUseCase(w.uow, FakeEmailSender()).execute(
                InviteTeamMemberCommand(
                    business_id=biz_a.id,
                    invited_by_user_id=owner_a.id,
                    email=f"{label}@example.com",
                    role=role,
                )
            )
            w.members[label] = m.id

    asyncio.run(build())

    app = create_app()

    async def fake_user(request: Request) -> User:
        return w.users[request.headers["x-test-user"]]

    app.dependency_overrides[get_current_local_user] = fake_user
    app.dependency_overrides[get_uow] = lambda: w.uow

    async def record(event: AuditEvent) -> None:
        w.audit.append(event)

    app.state.audit_recorder = record
    yield w, TestClient(app, raise_server_exceptions=False)
    limiter.enabled = True


def _call(client: TestClient, user: str, method: str, path: str, json: Any = None) -> int:
    return client.request(method, f"/api/v1{path}", headers={"x-test-user": user}, json=json).status_code


_ID = "00000000-0000-0000-0000-0000000000aa"

# (method, path template, json body). Bodies are deliberately minimal/invalid:
# only "was it 403?" matters, so 404/422 from the handler counts as allowed.
_PROBES: list[tuple[str, str, Any, tuple[BusinessRole, ...]]] = [
    ("GET", "/businesses/{b}", None, ANY_MEMBER),
    ("GET", "/businesses/{b}/sales", None, ANY_MEMBER),
    ("GET", "/businesses/{b}/expenses", None, ANY_MEMBER),
    ("GET", "/businesses/{b}/customers", None, ANY_MEMBER),
    ("GET", "/businesses/{b}/products", None, ANY_MEMBER),
    ("GET", "/businesses/{b}/purchases", None, ANY_MEMBER),
    ("GET", "/businesses/{b}/vendors", None, ANY_MEMBER),
    ("GET", "/businesses/{b}/dashboard/summary", None, ANY_MEMBER),
    ("GET", "/businesses/{b}/team-members", None, ANY_MEMBER),
    ("POST", "/businesses/{b}/sales", {}, CAN_WRITE),
    ("POST", "/businesses/{b}/expenses", {}, CAN_WRITE),
    ("POST", "/businesses/{b}/customers", {}, CAN_WRITE),
    ("POST", "/businesses/{b}/products", {}, CAN_WRITE),
    ("GET", "/businesses/{b}/dashboard/whatsapp-summary", None, ANY_MEMBER),
    ("GET", "/businesses/{b}/sales/receivables", None, ANY_MEMBER),
    ("GET", "/businesses/{b}/sales/next-invoice-number", None, ANY_MEMBER),
    ("GET", "/businesses/{b}/sales/" + _ID + "/invoice-pdf", None, ANY_MEMBER),
    ("POST", "/businesses/{b}/sales/" + _ID + "/share-link", None, CAN_WRITE),
    ("POST", "/businesses/{b}/sales/" + _ID + "/share-link/revoke", None, CAN_WRITE),
    ("POST", "/businesses/{b}/sales/" + _ID + "/payments", {}, CAN_WRITE),
    ("POST", "/businesses/{b}/sales/" + _ID + "/void", {}, CAN_WRITE),
    ("POST", "/businesses/{b}/expenses/" + _ID + "/void", {}, CAN_WRITE),
    ("POST", "/businesses/{b}/imports/customers/jobs", None, CAN_WRITE),
    ("GET", "/businesses/{b}/dashboard/profit-loss-pdf", None, CAN_EXPORT),
    ("POST", "/businesses/{b}/dashboard/profit-loss-pdf/email", {}, CAN_EXPORT),
    ("POST", "/businesses/{b}/team-members", {}, CAN_MANAGE_TEAM),
    ("PATCH", "/businesses/{b}/team-members/" + _ID, {}, CAN_MANAGE_TEAM),
    ("POST", "/businesses/{b}/team-members/" + _ID + "/remove", None, CAN_MANAGE_TEAM),
    ("PATCH", "/businesses/{b}/onboarding", {}, CAN_EDIT_SETTINGS),
    ("PATCH", "/businesses/{b}/plan", {}, OWNER_ONLY),
]
_ROLE_USERS = {
    BusinessRole.OWNER: "owner_a",
    BusinessRole.ADMIN: "admin",
    BusinessRole.ACCOUNTANT: "accountant",
    BusinessRole.VIEWER: "viewer",
}


_PROBE_IDS = [f"{m} {p}" for m, p, _, _ in _PROBES]


@pytest.mark.parametrize(("method", "path", "body", "allowed"), _PROBES, ids=_PROBE_IDS)
def test_each_role_gets_exactly_the_access_the_matrix_grants(
    world: tuple[World, TestClient], method: str, path: str, body: Any, allowed: tuple[BusinessRole, ...]
) -> None:
    w, client = world
    url = path.replace("{b}", str(w.business_a))
    for role, user in _ROLE_USERS.items():
        status = _call(client, user, method, url, body)
        permitted = not allowed or role in allowed
        if permitted:
            assert status != 403, f"{role.value} should be allowed on {method} {path}, got {status}"
        else:
            assert status == 403, f"{role.value} must be denied on {method} {path}, got {status}"


_PROBE_IDS = [f"{m} {p}" for m, p, _, _ in _PROBES]


@pytest.mark.parametrize(("method", "path", "body", "allowed"), _PROBES, ids=_PROBE_IDS)
def test_a_non_member_is_denied_everywhere_in_someone_elses_business(
    world: tuple[World, TestClient], method: str, path: str, body: Any, allowed: tuple[BusinessRole, ...]
) -> None:
    w, client = world
    url = path.replace("{b}", str(w.business_a))

    # Owner of business B, and a user with no membership anywhere.
    assert _call(client, "owner_b", method, url, body) == 403
    assert _call(client, "outsider", method, url, body) == 403


def test_a_removed_member_loses_access_on_the_very_next_request(world: tuple[World, TestClient]) -> None:
    w, client = world
    url = f"/businesses/{w.business_a}/sales"
    assert _call(client, "accountant", "GET", url) == 200

    remove_url = f"/businesses/{w.business_a}/team-members/{w.members['accountant']}/remove"
    assert _call(client, "owner_a", "POST", remove_url) == 200

    assert _call(client, "accountant", "GET", url) == 403


def test_a_role_change_takes_effect_on_the_very_next_request(world: tuple[World, TestClient]) -> None:
    w, client = world
    url = f"/businesses/{w.business_a}/expenses"
    assert _call(client, "accountant", "POST", url, {}) != 403

    changed = _call(
        client,
        "owner_a",
        "PATCH",
        f"/businesses/{w.business_a}/team-members/{w.members['accountant']}",
        {"role": "viewer"},
    )
    assert changed == 200

    assert _call(client, "accountant", "POST", url, {}) == 403
    assert _call(client, "accountant", "GET", url) == 200


def test_a_suspended_business_loses_access_until_reactivated(world: tuple[World, TestClient]) -> None:
    w, client = world
    url = f"/businesses/{w.business_a}/sales"
    assert _call(client, "owner_a", "GET", url) == 200

    import asyncio

    async def set_status(status: BusinessStatus) -> None:
        business = await w.uow.businesses.get_by_id(w.business_a)
        assert business is not None
        business.status = status
        await w.uow.businesses.update(business)

    asyncio.run(set_status(BusinessStatus.SUSPENDED))
    for user in ("owner_a", "admin", "accountant", "viewer"):
        assert _call(client, user, "GET", url) == 403, user
        assert _call(client, user, "GET", f"/businesses/{w.business_a}") == 403, user

    asyncio.run(set_status(BusinessStatus.ACTIVE))
    assert _call(client, "owner_a", "GET", url) == 200


def test_admin_cannot_grant_the_owner_role_by_invite_or_role_change(world: tuple[World, TestClient]) -> None:
    w, client = world
    base = f"/businesses/{w.business_a}/team-members"

    invite = _call(client, "admin", "POST", base, {"email": "outsider@example.com", "role": "owner"})
    change = _call(client, "admin", "PATCH", f"{base}/{w.members['viewer']}", {"role": "owner"})

    assert invite == 422
    assert change == 422


def test_admin_cannot_change_or_remove_the_owner(world: tuple[World, TestClient]) -> None:
    w, client = world
    import asyncio

    owner_membership = asyncio.run(
        w.uow.business_memberships.get_for_user_and_business(
            user_id=w.users["owner_a"].id, business_id=w.business_a
        )
    )
    assert owner_membership is not None
    base = f"/businesses/{w.business_a}/team-members/{owner_membership.id}"

    assert _call(client, "admin", "PATCH", base, {"role": "viewer"}) == 422
    assert _call(client, "admin", "POST", f"{base}/remove") == 422
    assert _call(client, "owner_a", "POST", f"{base}/remove") == 422  # nobody, the owner included


def test_a_member_cannot_escalate_their_own_role(world: tuple[World, TestClient]) -> None:
    w, client = world
    base = f"/businesses/{w.business_a}/team-members"

    assert _call(client, "admin", "PATCH", f"{base}/{w.members['admin']}", {"role": "accountant"}) == 422
    # Accountants and viewers cannot reach the team endpoints at all.
    assert _call(client, "viewer", "PATCH", f"{base}/{w.members['viewer']}", {"role": "admin"}) == 403
    assert _call(client, "accountant", "PATCH", f"{base}/{w.members['accountant']}", {"role": "admin"}) == 403


def test_a_membership_id_from_another_business_is_not_actionable(world: tuple[World, TestClient]) -> None:
    w, client = world
    import asyncio

    owner_b_membership = asyncio.run(
        w.uow.business_memberships.get_for_user_and_business(
            user_id=w.users["owner_b"].id, business_id=w.business_b
        )
    )
    assert owner_b_membership is not None

    # Owner A targets B's membership id through A's own (authorised) path.
    path = f"/businesses/{w.business_a}/team-members/{owner_b_membership.id}"
    assert _call(client, "owner_a", "PATCH", path, {"role": "viewer"}) == 404
    assert _call(client, "owner_a", "POST", f"{path}/remove") == 404


def test_inviting_an_already_registered_member_is_a_conflict(world: tuple[World, TestClient]) -> None:
    w, client = world

    status = _call(
        client,
        "owner_a",
        "POST",
        f"/businesses/{w.business_a}/team-members",
        {"email": "viewer@example.com", "role": "viewer"},
    )

    assert status == 409


def test_an_unauthenticated_request_is_rejected_before_any_role_logic() -> None:
    client = TestClient(create_app(), raise_server_exceptions=False)

    for path in ("/businesses", f"/businesses/{_ID}", f"/businesses/{_ID}/sales"):
        assert client.get(f"/api/v1{path}").status_code in (401, 403)


# ---------------------------------------------------------------- audit trail


def test_a_successful_mutation_is_audited_with_actor_business_and_record(
    world: tuple[World, TestClient],
) -> None:
    w, client = world
    membership_id = w.members["viewer"]

    status = _call(
        client,
        "owner_a",
        "PATCH",
        f"/businesses/{w.business_a}/team-members/{membership_id}",
        {"role": "accountant"},
    )

    assert status == 200
    (event,) = w.audit
    assert event.actor_user_id == w.users["owner_a"].id
    assert event.actor_role == "owner"
    assert event.business_id == w.business_a
    assert event.action == "PATCH /businesses/{business_id}/team-members/{membership_id}"
    assert event.entity_type == "membership"
    assert event.entity_id == membership_id
    assert event.status_code == 200


def test_denied_failed_and_read_requests_are_not_audited(world: tuple[World, TestClient]) -> None:
    w, client = world
    base = f"/businesses/{w.business_a}"

    _call(client, "viewer", "POST", f"{base}/expenses", {})  # 403
    owner_invite = {"email": "x@example.com", "role": "owner"}
    _call(client, "owner_a", "POST", f"{base}/team-members", owner_invite)  # 422
    _call(client, "owner_a", "GET", f"{base}/sales")  # a read

    assert w.audit == []


def test_audit_events_carry_no_request_payload_fields() -> None:
    assert set(AuditEvent.__dataclass_fields__) == {
        "business_id",
        "firm_id",
        "actor_user_id",
        "actor_role",
        "action",
        "entity_type",
        "entity_id",
        "status_code",
    }


def test_describe_reads_the_record_from_the_path_or_the_create_response() -> None:
    sale_id = uuid.uuid4()
    new_id = uuid.uuid4()

    void_path = "/api/v1/businesses/{business_id}/sales/{sale_id}/void"
    assert describe(void_path, {"sale_id": str(sale_id)}, b"") == ("sale", sale_id)
    assert describe("/api/v1/businesses/{business_id}/sales", {}, f'{{"id": "{new_id}"}}'.encode()) == (
        "sales",
        new_id,
    )
    assert describe("/api/v1/businesses/{business_id}/sales", {}, b"not json") == ("sales", None)


def _gst_sale_body() -> dict[str, Any]:
    return {
        "invoice_number": "INV-GST-1",
        "invoice_date": "2026-11-01",
        "line_items": [
            {
                "line_number": 1,
                "description": "Service",
                "quantity": "1",
                "unit_price": "1000",
                "gst_rate": "18",
                "hsn_code": "998314",
            }
        ],
        "place_of_supply": "27",
    }


def test_gst_fields_sent_to_the_api_are_used_and_returned(world: tuple[World, TestClient]) -> None:
    w, client = world
    base = f"/api/v1/businesses/{w.business_a}/sales"

    created = client.post(base, headers={"x-test-user": "owner_a"}, json=_gst_sale_body())

    assert created.status_code == 201, created.text
    sale = created.json()
    assert Decimal(sale["tax"]) == Decimal("180.00") and Decimal(sale["total_amount"]) == Decimal("1180.00")
    assert sale["place_of_supply"] == "27"
    assert sale["line_items"][0]["hsn_code"] == "998314"
    assert [Decimal(g["tax"]) for g in sale["gst_breakdown"]] == [Decimal("180.00")]

    edited = _gst_sale_body()
    edited["line_items"][0]["gst_rate"] = "5"
    edited["place_of_supply"] = "29"
    updated = client.patch(f"{base}/{sale['id']}", headers={"x-test-user": "owner_a"}, json=edited)

    assert updated.status_code == 200, updated.text
    assert Decimal(updated.json()["tax"]) == Decimal("50.00") and updated.json()["place_of_supply"] == "29"


def test_the_invoice_pdf_downloads_for_any_member(world: tuple[World, TestClient]) -> None:
    w, client = world
    base = f"/api/v1/businesses/{w.business_a}/sales"
    sale = client.post(base, headers={"x-test-user": "owner_a"}, json=_gst_sale_body()).json()

    response = client.get(f"{base}/{sale['id']}/invoice-pdf", headers={"x-test-user": "viewer"})

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert 'filename="invoice-INV-GST-1.pdf"' in response.headers["content-disposition"]


def _make_sale(client: TestClient, w: World) -> dict[str, Any]:
    base = f"/api/v1/businesses/{w.business_a}/sales"
    return client.post(base, headers={"x-test-user": "owner_a"}, json=_gst_sale_body()).json()


def _share(client: TestClient, w: World, sale_id: str, user: str = "owner_a") -> Any:
    url = f"/api/v1/businesses/{w.business_a}/sales/{sale_id}/share-link"
    return client.post(url, headers={"x-test-user": user})


def test_a_shared_invoice_opens_without_signing_in_until_revoked(world: tuple[World, TestClient]) -> None:
    w, client = world
    sale = _make_sale(client, w)

    created = _share(client, w, sale["id"])

    assert created.status_code == 201, created.text
    link = created.json()["url"]
    assert "/i/" in link
    token = link.rsplit("/", 1)[1]
    opened = client.get(f"/api/v1/public/invoices/{token}")  # no user header: the customer is not signed in
    assert opened.status_code == 200 and opened.content.startswith(b"%PDF-")
    assert opened.headers["content-disposition"].startswith("inline")
    assert opened.headers["cache-control"] == "private, no-store"
    assert "noindex" in opened.headers["x-robots-tag"]

    revoke_url = f"/api/v1/businesses/{w.business_a}/sales/{sale['id']}/share-link/revoke"
    assert client.post(revoke_url, headers={"x-test-user": "viewer"}).status_code == 403
    revoked = client.post(revoke_url, headers={"x-test-user": "owner_a"})
    assert revoked.status_code == 200 and revoked.json() == {"revoked": 1}
    assert client.get(f"/api/v1/public/invoices/{token}").status_code == 404


def test_a_guessed_or_garbled_invoice_link_is_not_found(world: tuple[World, TestClient]) -> None:
    _, client = world

    for token in ("nope", "A" * 32, "../etc/passwd"):
        assert client.get(f"/api/v1/public/invoices/{token}").status_code == 404


def test_only_people_who_can_write_make_links_and_never_across_businesses(
    world: tuple[World, TestClient],
) -> None:
    w, client = world
    sale = _make_sale(client, w)

    assert _share(client, w, sale["id"], user="viewer").status_code == 403
    # Business B's owner asks for business A's sale through business B's own path: not found
    other = f"/api/v1/businesses/{w.business_b}/sales/{sale['id']}/share-link"
    assert client.post(other, headers={"x-test-user": "owner_b"}).status_code == 404


def test_a_voided_invoice_cannot_be_shared(world: tuple[World, TestClient]) -> None:
    w, client = world
    sale = _make_sale(client, w)
    void_url = f"/api/v1/businesses/{w.business_a}/sales/{sale['id']}/void"
    assert client.post(void_url, headers={"x-test-user": "owner_a"}).status_code == 200

    assert _share(client, w, sale["id"]).status_code == 422


def test_the_udhaar_list_and_the_next_invoice_number_come_through_the_api(
    world: tuple[World, TestClient],
) -> None:
    w, client = world
    owner = {"x-test-user": "owner_a"}
    customers = f"/api/v1/businesses/{w.business_a}/customers"
    customer = client.post(customers, headers=owner, json={"name": "Asha", "phone": "9123456780"}).json()
    body = _gst_sale_body()
    body["customer_id"] = customer["id"]
    sales = f"/api/v1/businesses/{w.business_a}/sales"
    assert client.post(sales, headers=owner, json=body).status_code == 201

    owed = client.get(f"{sales}/receivables", headers={"x-test-user": "viewer"})

    assert owed.status_code == 200, owed.text
    data = owed.json()
    assert Decimal(data["total_outstanding"]) == Decimal("1180.00")
    (row,) = data["customers"]
    assert row["name"] == "Asha" and row["phone"] == "9123456780"
    assert [i["invoice_number"] for i in row["invoices"]] == ["INV-GST-1"]

    number = client.get(f"{sales}/next-invoice-number", headers=owner)
    assert number.status_code == 200 and number.json() == {"invoice_number": "INV-GST-2"}


def test_the_whatsapp_summary_and_its_setting_work_through_the_api(world: tuple[World, TestClient]) -> None:
    w, client = world
    owner = {"x-test-user": "owner_a"}
    base = f"/api/v1/businesses/{w.business_a}"
    today = datetime.now(timezone.utc).date().isoformat()
    sale = _gst_sale_body()
    sale["invoice_date"] = today
    assert client.post(f"{base}/sales", headers=owner, json=sale).status_code == 201

    summary = client.get(f"{base}/dashboard/whatsapp-summary?period=today", headers={"x-test-user": "viewer"})

    assert summary.status_code == 200, summary.text
    data = summary.json()
    # the Overview counts a sale at its full amount, tax included, and the summary matches it
    assert Decimal(data["sales_total"]) == Decimal("1180.00")
    assert Decimal(data["to_collect_total"]) == Decimal("1180.00")
    assert data["message"].startswith("*Biz A*") and "To collect (udhaar)" in data["message"]
    assert client.get(f"{base}/dashboard/whatsapp-summary?period=lastweek", headers=owner).status_code == 422
    hindi = client.get(f"{base}/dashboard/whatsapp-summary?period=today&lang=hi", headers=owner)
    assert hindi.status_code == 200 and "बिक्री:" in hindi.json()["message"]
    assert (
        client.get(f"{base}/dashboard/whatsapp-summary?period=today&lang=fr", headers=owner).status_code
        == 422
    )
    assert client.get(base, headers=owner).json()["language"] == "en"
    set_hindi = client.patch(f"{base}/onboarding", headers=owner, json={"language": "hi"})
    assert set_hindi.status_code == 200 and set_hindi.json()["language"] == "hi"
    assert client.patch(f"{base}/onboarding", headers=owner, json={"language": "fr"}).status_code == 422

    assert client.get(base, headers=owner).json()["summary_frequency"] == "off"
    on = client.patch(f"{base}/onboarding", headers=owner, json={"summary_frequency": "daily"})
    assert on.status_code == 200 and on.json()["summary_frequency"] == "daily"
    assert (
        client.patch(f"{base}/onboarding", headers=owner, json={"summary_frequency": "hourly"}).status_code
        == 422
    )
    assert (
        client.patch(
            f"{base}/onboarding", headers={"x-test-user": "viewer"}, json={"summary_frequency": "off"}
        ).status_code
        == 403
    )


def test_a_supplier_can_be_added_with_only_a_name(world: tuple[World, TestClient]) -> None:
    w, client = world
    vendors = f"/api/v1/businesses/{w.business_a}/vendors"
    owner = {"x-test-user": "owner_a"}

    created = client.post(vendors, headers=owner, json={"legal_name": "Gupta Wholesale"})

    assert created.status_code == 201, created.text
    assert created.json()["contact_email"] == "" and created.json()["tax_id_masked"] == ""
    assert client.get(f"{vendors}/{created.json()['id']}", headers=owner).status_code == 200
    bad = client.post(vendors, headers=owner, json={"legal_name": "B", "tax_id": "nonsense"})
    assert bad.status_code == 422
