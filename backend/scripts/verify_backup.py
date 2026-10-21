"""Check a (decrypted) backup file's integrity. No database, no app install.

    python backend/scripts/verify_backup.py backup.json [--max-age-hours 36]

Exit 0 and a one-line summary when intact; exit 1 and the problems otherwise.
Used by the backup workflow right after the dump, so a corrupt or empty backup
fails the job (and alerts the owner) instead of being stored as "green".
"""

import argparse
import datetime
import importlib.util
import json
import pathlib
import sys

# Load backup_format.py by path: it is standard-library only, and importing it
# as a package would pull in the app (and its dependencies) for no reason.
_FORMAT = (
    pathlib.Path(__file__).resolve().parents[1] / "app" / "shared" / "infrastructure" / "backup_format.py"
)
_spec = importlib.util.spec_from_file_location("backup_format", _FORMAT)
assert _spec and _spec.loader
backup_format = importlib.util.module_from_spec(_spec)
sys.modules["backup_format"] = backup_format
_spec.loader.exec_module(backup_format)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("backup")
    parser.add_argument("--max-age-hours", type=float, default=None)
    args = parser.parse_args()

    try:
        doc = json.loads(pathlib.Path(args.backup).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"BACKUP INVALID: cannot read {args.backup}: {exc}")
        return 1

    problems = backup_format.verify_backup(doc)
    manifest = doc.get("manifest", {}) if isinstance(doc, dict) else {}

    if args.max_age_hours is not None and manifest.get("generated_at"):
        age = datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(
            manifest["generated_at"]
        )
        if age > datetime.timedelta(hours=args.max_age_hours):
            problems.append(f"backup is {age} old (limit {args.max_age_hours}h)")

    if problems:
        print("BACKUP INVALID:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    tables = manifest["tables"]
    total = sum(t["rows"] for t in tables.values())
    print(
        f"BACKUP OK: {total} rows in {len(tables)} tables, schema {manifest['schema_version']}, "
        f"generated {manifest['generated_at']}, commit {manifest.get('app_commit') or 'unknown'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
