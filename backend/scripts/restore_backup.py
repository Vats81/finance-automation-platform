"""Restore a (decrypted) backup into an ISOLATED database and reconcile it.

    RESTORE_DATABASE_URL=postgresql://... \\
      python scripts/restore_backup.py backup.json --confirm-isolated --migrate \\
          --report restore-report.json [--expect expect.json]

Never point this at production. It refuses to run when the target looks like
the live database (same host and database name as DATABASE_URL) and requires
--confirm-isolated. It restores only into an empty database (or --truncate),
inside one transaction, so a failure changes nothing. External side effects
(email, WhatsApp, Stripe, Celery) are never touched: this script does not start
the app.

--migrate runs `alembic upgrade <backup schema version>` on the target first.
--expect takes JSON like {"[QA] Demo Bakery": {"sales_total": "3250.00",
"expenses_total": "1585.50", "profit": "1664.50"}} and fails if the restored
figures differ. Exit 0 only when the restore AND the reconciliation pass.
"""

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
from urllib.parse import urlsplit

from sqlalchemy import create_engine

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config.database_url import normalize_database_urls  # noqa: E402
from app.shared.infrastructure import backup_format as fmt  # noqa: E402
from app.shared.infrastructure import backup_tool as tool  # noqa: E402


def _identity(url: str) -> tuple[str, str]:
    parts = urlsplit(url.replace("+asyncpg", "").replace("+psycopg2", ""))
    return (parts.hostname or "", parts.path.lstrip("/"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("backup", help="decrypted backup JSON")
    parser.add_argument("--target-url", default=os.environ.get("RESTORE_DATABASE_URL"))
    parser.add_argument("--confirm-isolated", action="store_true")
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--truncate", action="store_true")
    parser.add_argument("--report", default="restore-report.json")
    parser.add_argument("--expect", default=None)
    args = parser.parse_args()

    if not args.target_url:
        print("Set RESTORE_DATABASE_URL (or --target-url) to the isolated database.")
        return 2
    if not args.confirm_isolated:
        print("Refusing to run without --confirm-isolated (this must never target production).")
        return 2

    _, target_sync = normalize_database_urls(args.target_url)
    for var in ("DATABASE_URL", "DATABASE_URL_SYNC"):
        live = os.environ.get(var)
        if live and _identity(live) == _identity(target_sync):
            print(f"Refusing: the target is the same database as ${var}. Use a separate, empty database.")
            return 2

    doc = json.loads(pathlib.Path(args.backup).read_text(encoding="utf-8"))
    problems = fmt.verify_backup(doc)
    if problems:
        print("Backup failed verification; nothing was restored:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    wanted = doc["manifest"]["schema_version"]

    expectations = json.loads(pathlib.Path(args.expect).read_text(encoding="utf-8")) if args.expect else None

    if args.migrate:
        print(f"Migrating the target to {wanted}...")
        env = {**os.environ, "DATABASE_URL_SYNC": target_sync, "DATABASE_URL": args.target_url}
        subprocess.run(["alembic", "upgrade", wanted], cwd=ROOT, env=env, check=True)

    engine = create_engine(target_sync)
    started = time.perf_counter()
    try:
        with engine.begin() as conn:
            restore = tool.restore_database(conn, doc, truncate=args.truncate)
    except tool.RestoreError as exc:
        print(f"RESTORE REFUSED: {exc}")
        return 1
    restore_seconds = time.perf_counter() - started

    with engine.connect() as conn:
        report = tool.reconcile(conn, doc, expectations=expectations)

    report["restore"] = {
        "backup_generated_at": doc["manifest"]["generated_at"],
        "backup_commit": doc["manifest"].get("app_commit"),
        "rows_restored": sum(restore["restored_rows"].values()),
        "restore_seconds": round(restore_seconds, 2),
    }
    pathlib.Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(
        f"Restored {report['restore']['rows_restored']} rows in {restore_seconds:.1f}s; "
        f"reconciliation {'PASSED' if report['ok'] else 'FAILED'}."
    )
    for mismatch in report["mismatches"]:
        print(f"  MISMATCH: {mismatch}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
