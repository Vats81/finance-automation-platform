"""Regression test for the container boot chain `alembic upgrade head &&
uvicorn ...` (backend/Dockerfile). When the database was unreachable
(expired free-tier Postgres), alembic exited non-zero, the `&&` stopped,
uvicorn never started, and the whole service went silent. Runs the real
alembic CLI against an address that refuses connections — no database or
Docker needed.
"""

import os
import subprocess
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[2]


def _run_alembic(args: list[str], database_url_sync: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DATABASE_URL_SYNC": database_url_sync}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=_BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_unreachable_database_does_not_stop_the_boot_chain() -> None:
    # Port 1 on localhost refuses connections immediately.
    result = _run_alembic(["upgrade", "head"], "postgresql+psycopg2://u:p@127.0.0.1:1/nodb")

    assert result.returncode == 0, result.stderr
    assert "Database unreachable, skipping migrations" in (result.stderr + result.stdout)


def test_offline_migration_rendering_is_unaffected() -> None:
    # The unreachable-database escape hatch only wraps the online connect;
    # offline SQL generation (no connection at all) must still work.
    result = _run_alembic(["upgrade", "0020:0021", "--sql"], "postgresql+psycopg2://u:p@127.0.0.1:1/nodb")

    assert result.returncode == 0, result.stderr
    assert "CREATE TABLE contact_requests" in result.stdout
