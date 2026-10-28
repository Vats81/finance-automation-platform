"""Firm-level actions leave a trail in the firm's own audit log; the log is for owner and admin only."""

from fastapi.testclient import TestClient

from tests.unit.firms.test_firms_api import World, add_client_business, api, build_firm, call  # noqa: F401


def _firm_events(w: World) -> list:
    return [e for e in w.audit if e.firm_id is not None]


def test_creating_a_firm_and_managing_staff_is_recorded(api: tuple[World, TestClient]) -> None:  # noqa: F811
    w, client = api
    firm_id, members = build_firm(w, client)
    call(client, "fowner", "PATCH", f"/firms/{firm_id}/staff/{members['fviewer']}", {"role": "accountant"})
    call(client, "fowner", "POST", f"/firms/{firm_id}/staff/{members['faccountant']}/remove")

    events = _firm_events(w)

    assert [e.action for e in events] == [
        "POST /firms",
        "POST /firms/{firm_id}/staff",
        "POST /firms/{firm_id}/staff",
        "POST /firms/{firm_id}/staff",
        "PATCH /firms/{firm_id}/staff/{membership_id}",
        "POST /firms/{firm_id}/staff/{membership_id}/remove",
    ]
    assert all(str(e.firm_id) == firm_id and e.business_id is None for e in events)
    assert {e.actor_role for e in events} == {"owner"}
    assert str(events[1].entity_id) == members["fadmin"]  # the new staff member's id
    assert str(events[4].entity_id) == members["fviewer"]


def test_adding_a_client_is_in_the_firm_trail_and_work_inside_it_is_in_the_clients(
    api: tuple[World, TestClient],  # noqa: F811
) -> None:
    w, client = api
    firm_id, _ = build_firm(w, client)
    business_id = add_client_business(client, firm_id)
    call(client, "faccountant", "POST", f"/businesses/{business_id}/customers", {"name": "Acme"})

    added = [e for e in _firm_events(w) if e.action == "POST /firms/{firm_id}/clients"]
    inside = [e for e in w.audit if e.business_id is not None and e.action.endswith("/customers")]

    assert len(added) == 1 and str(added[0].entity_id) == business_id
    assert len(inside) == 1 and inside[0].actor_role == "firm_accountant" and inside[0].firm_id is None


def test_reads_and_refused_requests_are_not_recorded(api: tuple[World, TestClient]) -> None:  # noqa: F811
    w, client = api
    firm_id, _ = build_firm(w, client)
    before = len(w.audit)

    call(client, "fviewer", "GET", f"/firms/{firm_id}/staff")
    call(
        client, "fviewer", "POST", f"/firms/{firm_id}/staff", {"email": "x@example.com", "role": "viewer"}
    )  # 403

    assert len(w.audit) == before


def test_a_new_client_can_start_in_rupees(api: tuple[World, TestClient]) -> None:  # noqa: F811
    w, client = api
    firm_id, _ = build_firm(w, client)

    rupees = call(
        client, "fowner", "POST", f"/firms/{firm_id}/clients", {"name": "Chai Co", "currency": "INR"}
    )
    default = call(client, "fowner", "POST", f"/firms/{firm_id}/clients", {"name": "Diner"})
    refused = call(
        client, "fowner", "POST", f"/firms/{firm_id}/clients", {"name": "Euro Co", "currency": "EUR"}
    )

    assert rupees.json()["currency"] == "INR"
    assert default.json()["currency"] == "USD"
    assert refused.status_code == 422
