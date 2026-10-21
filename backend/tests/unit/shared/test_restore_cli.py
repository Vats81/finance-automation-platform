"""The restore/verify command-line tools: their guard rails and happy path."""

import json
import os
import pathlib
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, text

from app.shared.infrastructure import backup_tool as tool
from app.shared.infrastructure.db.base import Base
from tests.unit.shared.test_backup_tool import REVISION, _new_engine, _seed_two_businesses

BACKEND = pathlib.Path(__file__).resolve().parents[3]
RESTORE = BACKEND / "scripts" / "restore_backup.py"
VERIFY = BACKEND / "scripts" / "verify_backup.py"


def _run(
    script: pathlib.Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    full_env = {**os.environ, **(env or {})}
    full_env.pop("DATABASE_URL", None)
    full_env.pop("DATABASE_URL_SYNC", None)
    full_env.update(env or {})
    return subprocess.run(
        [sys.executable, str(script), *args], capture_output=True, text=True, env=full_env, cwd=BACKEND
    )


@pytest.fixture
def backup_file(tmp_path: pathlib.Path) -> pathlib.Path:
    engine = _new_engine()
    with engine.begin() as conn:
        _seed_two_businesses(conn)
    with engine.connect() as conn:
        doc = tool.dump_database(conn, app_commit="abc1234")
    path = tmp_path / "backup.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _empty_target(tmp_path: pathlib.Path) -> str:
    url = f"sqlite:///{tmp_path / 'target.db'}"
    engine = create_engine(url)
    tool.backup_tables()
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.ext.compiler import compiles

    compiles(JSONB, "sqlite")(lambda *_a, **_k: "JSON")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(text("INSERT INTO alembic_version VALUES (:v)"), {"v": REVISION})
    engine.dispose()
    return url


def test_verify_accepts_an_intact_backup_and_rejects_a_tampered_one(
    backup_file: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    ok = _run(VERIFY, str(backup_file))
    doc = json.loads(backup_file.read_text(encoding="utf-8"))
    doc["tables"]["expenses"][0]["amount_cents"] += 1
    bad_file = tmp_path / "tampered.json"
    bad_file.write_text(json.dumps(doc), encoding="utf-8")
    bad = _run(VERIFY, str(bad_file))
    stale = _run(VERIFY, str(backup_file), "--max-age-hours", "0.0000001")

    assert ok.returncode == 0 and "BACKUP OK" in ok.stdout
    assert bad.returncode == 1 and "checksum mismatch" in bad.stdout
    assert stale.returncode == 1 and "old" in stale.stdout
    assert _run(VERIFY, str(tmp_path / "missing.json")).returncode == 1


def test_restore_requires_the_isolation_flag_and_a_target(
    backup_file: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    no_target = _run(RESTORE, str(backup_file), "--confirm-isolated")
    no_flag = _run(RESTORE, str(backup_file), "--target-url", _empty_target(tmp_path))

    assert no_target.returncode == 2
    assert no_flag.returncode == 2 and "--confirm-isolated" in no_flag.stdout


def test_restore_refuses_to_target_the_live_database(
    backup_file: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    live = _empty_target(tmp_path)

    result = _run(
        RESTORE, str(backup_file), "--confirm-isolated", "--target-url", live, env={"DATABASE_URL_SYNC": live}
    )

    assert result.returncode == 2
    assert "same database" in result.stdout


def test_restore_and_reconcile_succeed_and_write_a_report(
    backup_file: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    expect = tmp_path / "expect.json"
    expect.write_text(
        json.dumps(
            {"[QA] Demo Bakery": {"sales_total": "3250.00", "expenses_total": "1585.50", "profit": "1664.50"}}
        ),
        encoding="utf-8",
    )
    report_path = tmp_path / "report.json"

    result = _run(
        RESTORE,
        str(backup_file),
        "--confirm-isolated",
        "--target-url",
        _empty_target(tmp_path),
        "--expect",
        str(expect),
        "--report",
        str(report_path),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "reconciliation PASSED" in result.stdout
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert report["restore"]["backup_commit"] == "abc1234"
    assert report["restore"]["rows_restored"] > 0
    assert all(e["ok"] for e in report["expectations"])


def test_restore_fails_loudly_when_the_figures_do_not_match_expectations(
    backup_file: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    expect = tmp_path / "expect.json"
    expect.write_text(json.dumps({"[QA] Demo Bakery": {"profit": "9999.00"}}), encoding="utf-8")

    result = _run(
        RESTORE,
        str(backup_file),
        "--confirm-isolated",
        "--target-url",
        _empty_target(tmp_path),
        "--expect",
        str(expect),
        "--report",
        str(tmp_path / "r.json"),
    )

    assert result.returncode == 1
    assert "MISMATCH" in result.stdout and "profit expected 9999.00" in result.stdout
