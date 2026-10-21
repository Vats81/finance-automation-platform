"""Backup -> restore -> reconcile, end to end, on throwaway SQLite databases.

SQLite is not Postgres, so this proves the logic (what is dumped, that a
restore reproduces every row and total exactly, what is refused) but not
Postgres-specific behaviour; the monthly restore drill
(.github/workflows/restore-drill.yml) covers that against a real Postgres.
"""

import copy
import datetime
import uuid
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.ext.compiler import compiles

from app.shared.infrastructure import backup_format as fmt
from app.shared.infrastructure import backup_tool as tool
from app.shared.infrastructure.db.base import Base


@compiles(JSONB, "sqlite")
def _jsonb_as_json(_type: Any, _compiler: Any, **_kw: Any) -> str:
    return "JSON"


REVISION = "0022"


def _new_engine() -> Engine:
    engine = create_engine("sqlite://")
    tool.backup_tables()  # loads every model into Base.metadata
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(text("INSERT INTO alembic_version VALUES (:v)"), {"v": REVISION})
    return engine


def _table(name: str) -> Any:
    return Base.metadata.tables[name]


def _insert(conn: Connection, table_name: str, /, **values: Any) -> uuid.UUID:
    row_id = values.setdefault("id", uuid.uuid4())
    conn.execute(_table(table_name).insert().values(**values))
    return row_id  # type: ignore[no-any-return]


def _seed_two_businesses(conn: Connection) -> dict[str, uuid.UUID]:
    ids: dict[str, uuid.UUID] = {}
    ids["owner"] = _insert(
        conn,
        "users",
        email="owner@example.com",
        display_name="Owner",
        role="ap_clerk",
        password_hash="$2b$12$abcdefghijklmnopqrstuv",
        email_verification_token_hash="tok-hash",
        password_reset_token_hash="reset-hash",
        is_email_verified=True,
    )
    ids["other_owner"] = _insert(conn, "users", email="o2@example.com", display_name="O2", role="ap_clerk")
    ids["viewer"] = _insert(conn, "users", email="viewer@example.com", display_name="V", role="ap_clerk")
    ids["bakery"] = _insert(conn, "businesses", owner_user_id=ids["owner"], name="[QA] Demo Bakery")
    ids["other"] = _insert(conn, "businesses", owner_user_id=ids["other_owner"], name="[QA] Other Co")
    _insert(
        conn,
        "business_memberships",
        business_id=ids["bakery"],
        user_id=ids["owner"],
        role="owner",
        status="active",
    )
    _insert(
        conn,
        "business_memberships",
        business_id=ids["bakery"],
        user_id=ids["viewer"],
        role="viewer",
        status="active",
    )
    _insert(
        conn,
        "business_memberships",
        business_id=ids["other"],
        user_id=ids["other_owner"],
        role="owner",
        status="active",
    )
    customer = _insert(conn, "customers", business_id=ids["bakery"], name="[QA] Acme Cafe")
    d = datetime.date(2026, 10, 3)
    for number, qty, price in (("QA-001", "2", 50000), ("QA-002", "1", 150000), ("QA-003", "3", 25000)):
        _insert(
            conn,
            "sales",
            business_id=ids["bakery"],
            customer_id=customer,
            invoice_number=number,
            invoice_date=d,
            line_items=[{"line_number": 1, "description": "x", "quantity": qty, "unit_price_cents": price}],
            amount_received_cents=100000 if number == "QA-001" else 0,
        )
    for category, cents, method in (
        ("Rent", 120000, "bank_transfer"),
        ("Software", 30000, "card"),
        ("Supplies", 8550, "cash"),
    ):
        _insert(
            conn,
            "expenses",
            business_id=ids["bakery"],
            expense_date=d,
            category=category,
            description=category,
            amount_cents=cents,
            payment_method=method,
        )
    _insert(
        conn,
        "products",
        business_id=ids["bakery"],
        name="Flour",
        sku="F-1",
        selling_price_cents=500,
        purchase_cost_cents=300,
        current_quantity=Decimal("12.5000"),
    )
    _insert(
        conn,
        "sales",
        business_id=ids["other"],
        invoice_number="OTHER-1",
        invoice_date=d,
        line_items=[{"line_number": 1, "description": "y", "quantity": "1", "unit_price_cents": 99900}],
    )
    _insert(conn, "contact_requests", name="Visitor", email="v@example.com")
    _insert(
        conn,
        "business_audit_events",
        business_id=ids["bakery"],
        actor_user_id=ids["owner"],
        actor_role="owner",
        action="POST /x",
        entity_type="sales",
        status_code=201,
    )
    _insert(
        conn,
        "outbox_messages",
        event_id=uuid.uuid4(),
        event_type="X",
        aggregate_id=uuid.uuid4(),
        payload={"a": 1},
        occurred_at=datetime.datetime.now(datetime.timezone.utc),
    )
    return ids


@pytest.fixture
def source() -> Engine:
    engine = _new_engine()
    with engine.begin() as conn:
        _seed_two_businesses(conn)
    return engine


def _backup(engine: Engine) -> dict[str, Any]:
    with engine.connect() as conn:
        return tool.dump_database(conn, app_commit="abc1234")


# ------------------------------------------------------------------- the dump


def test_dump_includes_every_table_and_a_valid_manifest(source: Engine) -> None:
    doc = _backup(source)

    assert fmt.verify_backup(doc) == []
    assert doc["manifest"]["schema_version"] == REVISION
    assert doc["manifest"]["app_commit"] == "abc1234"
    assert set(doc["tables"]) == {t.name for t in tool.backup_tables()}
    assert doc["manifest"]["tables"]["sales"]["rows"] == 4
    # line items travel inside the sale row
    qa1 = next(s for s in doc["tables"]["sales"] if s["invoice_number"] == "QA-001")
    assert qa1["line_items"][0]["unit_price_cents"] == 50000


def test_dump_leaves_out_the_outbox_and_one_time_tokens_but_keeps_password_hashes(source: Engine) -> None:
    doc = _backup(source)

    assert "outbox_messages" not in doc["tables"]
    assert "alembic_version" not in doc["tables"]
    owner = next(u for u in doc["tables"]["users"] if u["email"] == "owner@example.com")
    assert "email_verification_token_hash" not in owner
    assert "password_reset_token_hash" not in owner
    assert owner["password_hash"].startswith("$2b$")


# ----------------------------------------------------------------- integrity


def test_verification_catches_tampering_and_truncation(source: Engine) -> None:
    doc = _backup(source)

    altered = copy.deepcopy(doc)
    altered["tables"]["expenses"][0]["amount_cents"] += 1
    truncated = copy.deepcopy(doc)
    truncated["tables"]["sales"].pop()
    no_version = copy.deepcopy(doc)
    no_version["manifest"]["schema_version"] = None

    assert any("expenses: checksum mismatch" in p for p in fmt.verify_backup(altered))
    assert any("sales: manifest says 4 rows" in p for p in fmt.verify_backup(truncated))
    assert any("schema_version" in p for p in fmt.verify_backup(no_version))
    assert fmt.verify_backup({"nope": 1})
    assert any("no rows" in p for p in fmt.verify_backup({**doc, "tables": {**doc["tables"], "users": []}}))


def test_checksum_ignores_row_order() -> None:
    rows = [{"id": "b", "v": 1}, {"id": "a", "v": 2}]

    assert fmt.table_checksum(rows) == fmt.table_checksum(list(reversed(rows)))


# ------------------------------------------------------------ restore + reconcile


def test_restore_reproduces_every_row_and_total_exactly(source: Engine) -> None:
    doc = _backup(source)
    target = _new_engine()

    with target.begin() as conn:
        result = tool.restore_database(conn, doc)
    with target.connect() as conn:
        report = tool.reconcile(
            conn,
            doc,
            expectations={
                "[QA] Demo Bakery": {
                    "sales_total": "3250.00",
                    "expenses_total": "1585.50",
                    "profit": "1664.50",
                }
            },
        )

    assert result["restored_rows"]["sales"] == 4
    assert report["ok"], report["mismatches"]
    assert all(t["checksum_match"] for t in report["per_table"].values())
    assert report["orphans"] == {}
    bakery = next(b for b in report["per_business"].values() if b["name"] == "[QA] Demo Bakery")
    assert bakery["sales_total"] == "3250.00"
    assert bakery["sales_received"] == "1000.00"
    assert bakery["sales_outstanding"] == "2250.00"
    assert bakery["expenses_total"] == "1585.50"
    assert bakery["profit"] == "1664.50"
    assert bakery["inventory_quantity"] == "12.5000"
    assert len(bakery["memberships"]) == 2
    assert all(e["ok"] for e in report["expectations"])


def test_restore_keeps_tenants_separate(source: Engine) -> None:
    doc = _backup(source)
    target = _new_engine()
    with target.begin() as conn:
        tool.restore_database(conn, doc)

    with target.connect() as conn:
        report = tool.reconcile(conn, doc)

    other = next(b for b in report["per_business"].values() if b["name"] == "[QA] Other Co")
    assert other["row_counts"]["sales"] == 1
    assert other["sales_total"] == "999.00"
    assert other["expenses_total"] == "0.00"


def test_reconcile_flags_a_restored_database_that_differs(source: Engine) -> None:
    doc = _backup(source)
    target = _new_engine()
    with target.begin() as conn:
        tool.restore_database(conn, doc)
        conn.execute(text("UPDATE expenses SET amount_cents = amount_cents + 100 WHERE category = 'Rent'"))

    with target.connect() as conn:
        report = tool.reconcile(conn, doc, expectations={"[QA] Demo Bakery": {"expenses_total": "1585.50"}})

    assert report["ok"] is False
    assert any("table expenses" in m for m in report["mismatches"])
    assert any("expenses_total expected 1585.50" in m for m in report["mismatches"])


def test_restore_refuses_a_non_empty_target_a_wrong_schema_and_a_bad_backup(source: Engine) -> None:
    doc = _backup(source)

    populated = _new_engine()
    with populated.begin() as conn:
        _insert(conn, "users", email="x@example.com", display_name="X", role="ap_clerk")
    with populated.begin() as conn, pytest.raises(tool.RestoreError, match="not empty"):
        tool.restore_database(conn, doc)

    old_schema = _new_engine()
    with old_schema.begin() as conn:
        conn.execute(text("UPDATE alembic_version SET version_num = '0019'"))
    with old_schema.begin() as conn, pytest.raises(tool.RestoreError, match="alembic upgrade 0022"):
        tool.restore_database(conn, doc)

    tampered = copy.deepcopy(doc)
    tampered["tables"]["users"][0]["email"] = "evil@example.com"
    fresh = _new_engine()
    with fresh.begin() as conn, pytest.raises(tool.RestoreError, match="failed verification"):
        tool.restore_database(conn, tampered)
    with fresh.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM users")).scalar_one() == 0


def test_a_failed_restore_leaves_the_target_untouched(source: Engine) -> None:
    doc = copy.deepcopy(_backup(source))
    # Valid manifest, but a row that violates a NOT NULL constraint partway through.
    doc["tables"]["expenses"][0]["category"] = None
    doc["manifest"]["tables"]["expenses"]["sha256"] = fmt.table_checksum(doc["tables"]["expenses"])
    target = _new_engine()

    with pytest.raises(Exception):  # noqa: B017, PT011 - any DB error; the point is the rollback
        with target.begin() as conn:
            tool.restore_database(conn, doc)

    with target.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM users")).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM businesses")).scalar_one() == 0


def test_truncate_replaces_an_existing_target(source: Engine) -> None:
    doc = _backup(source)
    target = _new_engine()
    with target.begin() as conn:
        _insert(conn, "users", email="stale@example.com", display_name="Stale", role="ap_clerk")

    with target.begin() as conn:
        tool.restore_database(conn, doc, truncate=True)

    with target.connect() as conn:
        assert tool.reconcile(conn, doc)["ok"]
        assert (
            conn.execute(text("SELECT count(*) FROM users WHERE email = 'stale@example.com'")).scalar_one()
            == 0
        )


def test_a_backup_round_trips_through_json_text(source: Engine) -> None:
    import json

    doc = json.loads(json.dumps(_backup(source)))
    target = _new_engine()

    with target.begin() as conn:
        tool.restore_database(conn, doc)
    with target.connect() as conn:
        assert tool.reconcile(conn, doc)["ok"]
