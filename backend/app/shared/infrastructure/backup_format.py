"""The on-disk format of a platform backup, and how to check one.

Standard library only, so the integrity check can run anywhere (the backup
workflow runs it on a bare CI runner) without installing the app.

A backup is one JSON document:

    {
      "manifest": {
        "format_version": 1,
        "generated_at": "2026-10-21T03:17:02+00:00",
        "app_commit": "abc1234",
        "schema_version": "0022",            # alembic revision of the source DB
        "tables": {"sales": {"rows": 3, "sha256": "..."}, ...}
      },
      "tables": {"sales": [ {...row...}, ... ], ...}
    }

Every table in the schema is included (not a hand-kept list), so a new table
cannot be silently left out of backups. Excluded on purpose:

* ``outbox_messages`` - the event relay queue. Restoring it would replay
  already-delivered events (emails, WhatsApp messages) from the past.
* One-time token hashes (email verification, password reset); they expire and
  restoring them would only resurrect stale links.

Password hashes ARE included: without them every user would have to reset a
password after a restore, which needs working email. That is acceptable only
because the file is encrypted before it leaves the runner and the endpoint is
platform-admin only (see docs/RECOVERY_RUNBOOK.md).
"""

import datetime
import decimal
import hashlib
import json
import uuid
from typing import Any

FORMAT_VERSION = 1

EXCLUDED_TABLES = frozenset({"outbox_messages", "alembic_version"})
EXCLUDED_COLUMNS: dict[str, frozenset[str]] = {
    "users": frozenset({"email_verification_token_hash", "password_reset_token_hash"}),
}


def to_json_value(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime.datetime | datetime.date):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    return value


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _row_key(row: dict[str, Any]) -> str:
    return str(row.get("id", "")) + canonical_json(row).decode("utf-8")


def table_checksum(rows: list[dict[str, Any]]) -> str:
    """Order-independent sha256 of a table's rows."""
    digest = hashlib.sha256()
    for row in sorted(rows, key=_row_key):
        digest.update(canonical_json(row))
        digest.update(b"\n")
    return digest.hexdigest()


def build_manifest(
    tables: dict[str, list[dict[str, Any]]],
    *,
    schema_version: str | None,
    app_commit: str,
    generated_at: datetime.datetime,
) -> dict[str, Any]:
    return {
        "format_version": FORMAT_VERSION,
        "generated_at": generated_at.isoformat(),
        "app_commit": app_commit,
        "schema_version": schema_version,
        "tables": {
            name: {"rows": len(rows), "sha256": table_checksum(rows)} for name, rows in sorted(tables.items())
        },
    }


def verify_backup(doc: Any, *, required_tables: tuple[str, ...] = ("users", "businesses")) -> list[str]:
    """Problems with a backup document; an empty list means it is intact."""
    if not isinstance(doc, dict) or "manifest" not in doc or "tables" not in doc:
        return ["not a backup document (missing manifest/tables)"]
    manifest, tables = doc["manifest"], doc["tables"]
    problems: list[str] = []

    if manifest.get("format_version") != FORMAT_VERSION:
        problems.append(f"unsupported format_version {manifest.get('format_version')!r}")
    if not manifest.get("schema_version"):
        problems.append("manifest has no schema_version (cannot restore against the right migration)")
    if not manifest.get("generated_at"):
        problems.append("manifest has no generated_at")

    declared = manifest.get("tables", {})
    if set(declared) != set(tables):
        problems.append(f"manifest and data list different tables: {sorted(set(declared) ^ set(tables))}")
    for name, rows in tables.items():
        entry = declared.get(name)
        if entry is None:
            continue
        if entry.get("rows") != len(rows):
            problems.append(f"{name}: manifest says {entry.get('rows')} rows, found {len(rows)}")
        elif entry.get("sha256") != table_checksum(rows):
            problems.append(f"{name}: checksum mismatch (data was altered or truncated)")
    for name in required_tables:
        if not tables.get(name):
            problems.append(f"{name}: no rows; a production backup should never be empty here")
    return problems
