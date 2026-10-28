"""Removes the throwaway QA data from a running deployment, through its admin API.

Everything whose name or display name starts with "[QA]" is a test artefact: businesses, firms,
users, beta waitlist rows and demo-request messages, plus any business owned by a QA user.
By default this only LISTS what it would delete. Nothing is removed without --apply.

Credentials come from the environment, never the command line or a file:

    set FINVERLO_API=https://finance-automation-platform-1.onrender.com/api/v1
    set ADMIN_EMAIL=you@example.com
    set ADMIN_PASSWORD=...
    python scripts/purge_qa_data.py            (preview)
    python scripts/purge_qa_data.py --apply    (delete)

Add --keep someone@example.com (repeatable) to spare a QA user, e.g. the demo account, along
with the businesses it owns. Deletion order matters and is handled here: businesses, then
firms, then users. Platform admins are never deleted by the API.
"""

import argparse
import os
import sys

import httpx

MARKER = "[QA]"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--apply", action="store_true", help="actually delete (default is a preview)")
    parser.add_argument("--keep", action="append", default=[], metavar="EMAIL", help="spare this QA user")
    args = parser.parse_args()

    base = os.environ.get("FINVERLO_API", "").rstrip("/")
    email, password = os.environ.get("ADMIN_EMAIL", ""), os.environ.get("ADMIN_PASSWORD", "")
    if not (base and email and password):
        print("Set FINVERLO_API, ADMIN_EMAIL and ADMIN_PASSWORD in the environment first.")
        return 2
    keep = {e.lower() for e in args.keep}

    client = httpx.Client(timeout=120)
    login = client.post(f"{base}/auth/login", json={"email": email, "password": password})
    if login.status_code != 200:
        print(f"Login failed ({login.status_code}).")
        return 2
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    def get(path: str, **params: object) -> httpx.Response:
        return client.get(f"{base}{path}", headers=headers, params=params)

    def pages(path: str) -> list[dict]:
        items: list[dict] = []
        offset = 0
        while True:
            body = get(path, offset=offset, limit=200).json()
            items += body["items"]
            offset += 200
            if offset >= body["total"]:
                return items

    users = pages("/admin/users")
    businesses = pages("/admin/businesses")
    firms = get("/admin/firms").json()
    waitlist = get("/admin/beta-waitlist").json()
    contacts = get("/admin/contact-requests").json()
    contact_items = contacts["items"] if isinstance(contacts, dict) else contacts

    qa_users = [u for u in users if u["display_name"].startswith(MARKER) and u["email"].lower() not in keep]
    qa_emails = {u["email"].lower() for u in qa_users}
    spared = {u["email"].lower() for u in users if u["email"].lower() in keep}
    qa_businesses = [
        b
        for b in businesses
        if b["owner_email"].lower() not in spared
        and (b["name"].startswith(MARKER) or b["owner_email"].lower() in qa_emails)
    ]
    qa_firms = [
        f
        for f in firms
        if f["owner_email"].lower() not in spared
        and (f["name"].startswith(MARKER) or f["owner_email"].lower() in qa_emails)
    ]
    qa_waitlist = [
        w for w in waitlist if w["name"].startswith(MARKER) or (w["business_name"] or "").startswith(MARKER)
    ]
    qa_contacts = [c for c in contact_items if str(c.get("name", "")).startswith(MARKER)]

    print(f"{'DELETING' if args.apply else 'PREVIEW (nothing will be deleted)'}")
    print(f"  businesses:    {len(qa_businesses)} of {len(businesses)}")
    print(f"  firms:         {len(qa_firms)} of {len(firms)}")
    print(f"  users:         {len(qa_users)} of {len(users)}")
    print(f"  waitlist rows: {len(qa_waitlist)} of {len(waitlist)}")
    print(f"  demo requests: {len(qa_contacts)} of {len(contact_items)}")
    for b in qa_businesses:
        print(f"    business  {b['name']}  ({b['owner_email']})")
    for f in qa_firms:
        print(f"    firm      {f['name']}  ({f['owner_email']}, {f['client_count']} clients)")
    for u in qa_users:
        print(f"    user      {u['email']}")
    if not args.apply:
        print("\nRe-run with --apply to delete these.")
        return 0

    failures: list[str] = []

    def delete(label: str, path: str, **params: str) -> None:
        r = client.delete(f"{base}{path}", headers=headers, params=params)
        if r.status_code not in (200, 204, 404):
            failures.append(f"{label}: {r.status_code} {r.text[:150]}")

    for b in qa_businesses:
        delete(f"business {b['name']}", f"/admin/businesses/{b['id']}", confirm_name=b["name"])
    for f in qa_firms:
        delete(f"firm {f['name']}", f"/admin/firms/{f['id']}", confirm_name=f["name"])
    for u in qa_users:
        delete(f"user {u['email']}", f"/admin/users/{u['id']}", confirm_email=u["email"])
    for w in qa_waitlist:
        delete(f"waitlist {w['work_email']}", f"/admin/beta-waitlist/{w['id']}")
    for c in qa_contacts:
        delete(f"demo request {c.get('id')}", f"/admin/contact-requests/{c['id']}")

    stats = get("/admin/stats").json()
    print(
        f"\nDone. The platform now has {stats['total_businesses']} businesses and {stats['total_users']} users."
    )
    if failures:
        print("\nThese were not deleted:")
        for line in failures:
            print("  " + line)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
