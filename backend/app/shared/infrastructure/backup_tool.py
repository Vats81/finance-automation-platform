"""Dump, restore and reconcile a database against a backup document.

Works on a synchronous SQLAlchemy Connection so the same code serves the
admin backup endpoint (via AsyncSession.run_sync), the restore CLI and the
tests. The format itself lives in backup_format.py.
"""

import datetime
import decimal
import os
import time
import uuid
from typing import Any

from sqlalchemy import Table, delete, func, select, text
from sqlalchemy import types as sqltypes
from sqlalchemy.engine import Connection

from app.shared.infrastructure import backup_format as fmt
from app.shared.infrastructure.db.base import Base

_BATCH = 500


def backup_tables() -> list[Table]:
    import app.api.main_router  # noqa: F401 - importing the routers loads every ORM model

    return [t for t in Base.metadata.sorted_tables if t.name not in fmt.EXCLUDED_TABLES]


def schema_version(conn: Connection) -> str | None:
    try:
        return conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    except Exception:  # noqa: BLE001 - no alembic table (e.g. a fresh test database)
        return None


def _included_columns(table: Table) -> list[str]:
    excluded = fmt.EXCLUDED_COLUMNS.get(table.name, frozenset())
    return [c.key for c in table.columns if c.key not in excluded]


def dump_tables(conn: Connection) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for table in backup_tables():
        keys = _included_columns(table)
        rows = conn.execute(select(*[table.c[k] for k in keys])).mappings().all()
        out[table.name] = [{k: fmt.to_json_value(row[k]) for k in keys} for row in rows]
    return out


def dump_database(
    conn: Connection, *, app_commit: str | None = None, now: datetime.datetime | None = None
) -> dict[str, Any]:
    tables = dump_tables(conn)
    manifest = fmt.build_manifest(
        tables,
        schema_version=schema_version(conn),
        app_commit=app_commit if app_commit is not None else os.environ.get("RENDER_GIT_COMMIT", "")[:7],
        generated_at=now or datetime.datetime.now(datetime.timezone.utc),
    )
    return {"manifest": manifest, "tables": tables}


def _from_json(column: Any, value: Any) -> Any:
    if value is None:
        return None
    type_ = column.type
    if isinstance(type_, sqltypes.Uuid):
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
    if isinstance(type_, sqltypes.DateTime):
        return datetime.datetime.fromisoformat(value)
    if isinstance(type_, sqltypes.Date):
        return datetime.date.fromisoformat(value)
    if isinstance(type_, sqltypes.Numeric):
        return decimal.Decimal(str(value))
    return value


class RestoreError(Exception):
    pass


def restore_database(conn: Connection, doc: dict[str, Any], *, truncate: bool = False) -> dict[str, Any]:
    """Loads a verified backup into an (isolated) database. Refuses a document
    that fails verification, a schema at a different migration, or a target
    that already holds data (unless truncate is set). Runs inside the caller's
    transaction, so a failure leaves the target untouched.
    """
    problems = fmt.verify_backup(doc)
    if problems:
        raise RestoreError("backup failed verification: " + "; ".join(problems))
    wanted = doc["manifest"]["schema_version"]
    actual = schema_version(conn)
    if actual != wanted:
        raise RestoreError(
            f"target schema is at migration {actual!r} but the backup is from {wanted!r}; "
            f"run `alembic upgrade {wanted}` against the target first"
        )

    tables = backup_tables()
    unknown = set(doc["tables"]) - {t.name for t in tables}
    if unknown:
        raise RestoreError(f"backup has tables this schema does not: {sorted(unknown)}")

    occupied = [t.name for t in tables if conn.execute(select(func.count()).select_from(t)).scalar_one() > 0]
    if occupied and not truncate:
        raise RestoreError(f"target database is not empty ({occupied}); restore only into a fresh database")
    if occupied:
        for table in reversed(tables):
            conn.execute(delete(table))

    started = time.perf_counter()
    restored: dict[str, int] = {}
    for table in tables:
        rows = doc["tables"].get(table.name, [])
        for i in range(0, len(rows), _BATCH):
            batch = [
                {k: _from_json(table.c[k], v) for k, v in row.items() if k in table.c}
                for row in rows[i : i + _BATCH]
            ]
            conn.execute(table.insert(), batch)
        restored[table.name] = len(rows)
    return {"restored_rows": restored, "seconds": round(time.perf_counter() - started, 3)}


# ------------------------------------------------------------------ reconcile


def _cents(value: Any) -> int:
    return int(value or 0)


def _sale_total_cents(sale: dict[str, Any]) -> int:
    lines = 0
    for item in sale.get("line_items") or []:
        qty = decimal.Decimal(str(item["quantity"]))
        lines += int(
            (qty * item["unit_price_cents"]).quantize(decimal.Decimal("1"), rounding=decimal.ROUND_HALF_UP)
        )
    return lines - _cents(sale.get("discount_cents")) + _cents(sale.get("tax_cents"))


def _money(cents: int) -> str:
    return f"{decimal.Decimal(cents) / 100:.2f}"


def business_summaries(tables: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    """Per-business figures computed from serialised rows, so the same function
    describes both a backup file and a restored database.
    """
    import app.api.main_router  # noqa: F401

    scoped = [t.name for t in Base.metadata.sorted_tables if "business_id" in t.c and t.name in tables]
    out: dict[str, dict[str, Any]] = {}
    for biz in tables.get("businesses", []):
        bid = biz["id"]
        counts = {name: sum(1 for r in tables[name] if r.get("business_id") == bid) for name in scoped}
        sales = [s for s in tables.get("sales", []) if s["business_id"] == bid and s.get("status") != "void"]
        expenses = [
            e for e in tables.get("expenses", []) if e["business_id"] == bid and e.get("status") != "void"
        ]
        products = [p for p in tables.get("products", []) if p["business_id"] == bid]
        sales_total = sum(_sale_total_cents(s) for s in sales)
        received = sum(_cents(s.get("amount_received_cents")) for s in sales)
        expense_total = sum(_cents(e.get("amount_cents")) for e in expenses)
        out[bid] = {
            "name": biz.get("name"),
            "owner_user_id": biz.get("owner_user_id"),
            "status": biz.get("status"),
            "row_counts": counts,
            "sales_total": _money(sales_total),
            "sales_received": _money(received),
            "sales_outstanding": _money(sales_total - received),
            "expenses_total": _money(expense_total),
            "profit": _money(sales_total - expense_total),
            "inventory_quantity": str(
                sum(decimal.Decimal(str(p.get("current_quantity") or 0)) for p in products)
            ),
            "memberships": sorted(
                f"{m['user_id']}:{m['role']}:{m['status']}"
                for m in tables.get("business_memberships", [])
                if m["business_id"] == bid
            ),
        }
    return out


def _orphans(tables: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    """Rows pointing at a business or user that does not exist."""
    business_ids = {b["id"] for b in tables.get("businesses", [])}
    user_ids = {u["id"] for u in tables.get("users", [])}
    found: dict[str, int] = {}
    for name, rows in tables.items():
        if rows and "business_id" in rows[0]:
            bad = sum(1 for r in rows if r.get("business_id") not in business_ids)
            if bad:
                found[f"{name}.business_id"] = bad
    bad_users = sum(1 for m in tables.get("business_memberships", []) if m["user_id"] not in user_ids)
    if bad_users:
        found["business_memberships.user_id"] = bad_users
    bad_owners = sum(1 for b in tables.get("businesses", []) if b["owner_user_id"] not in user_ids)
    if bad_owners:
        found["businesses.owner_user_id"] = bad_owners
    return found


def reconcile(
    conn: Connection, doc: dict[str, Any], *, expectations: dict[str, dict[str, str]] | None = None
) -> dict[str, Any]:
    """Compares a restored database with the backup it came from, table by
    table (row counts and checksums) and business by business (counts, money
    totals, stock, memberships), plus referential sanity and optional known
    figures (expectations: business name -> {sales_total, expenses_total, ...}).
    """
    restored = dump_tables(conn)
    expected_tables = doc["tables"]
    mismatches: list[str] = []

    per_table = {}
    for name in sorted(set(expected_tables) | set(restored)):
        want, got = expected_tables.get(name, []), restored.get(name, [])
        same = len(want) == len(got) and fmt.table_checksum(want) == fmt.table_checksum(got)
        per_table[name] = {"backup_rows": len(want), "restored_rows": len(got), "checksum_match": same}
        if not same:
            mismatches.append(
                f"table {name}: backup {len(want)} rows vs restored {len(got)}, or checksum differs"
            )

    want_summary, got_summary = business_summaries(expected_tables), business_summaries(restored)
    if want_summary != got_summary:
        mismatches.append("per-business summaries differ between backup and restored database")

    orphans = _orphans(restored)
    if orphans:
        mismatches.append(f"orphaned rows after restore: {orphans}")

    version_ok = schema_version(conn) == doc["manifest"]["schema_version"]
    if not version_ok:
        mismatches.append("schema version differs from the backup's")

    checked: list[dict[str, Any]] = []
    for business_name, wanted in (expectations or {}).items():
        match = next((s for s in got_summary.values() if s["name"] == business_name), None)
        if match is None:
            mismatches.append(f"expected business {business_name!r} not found after restore")
            continue
        for key, value in wanted.items():
            ok = str(match.get(key)) == str(value)
            checked.append(
                {
                    "business": business_name,
                    "field": key,
                    "expected": value,
                    "actual": match.get(key),
                    "ok": ok,
                }
            )
            if not ok:
                mismatches.append(f"{business_name}: {key} expected {value}, got {match.get(key)}")

    return {
        "ok": not mismatches,
        "mismatches": mismatches,
        "schema_version": {"backup": doc["manifest"]["schema_version"], "restored": schema_version(conn)},
        "per_table": per_table,
        "per_business": got_summary,
        "orphans": orphans,
        "expectations": checked,
    }
