"""One-time seed script for a freshly-deployed environment.

Run this from the deployed backend's own shell (e.g. Render's "Shell" tab,
paid plans only — see the /internal/seed-demo-users route for a free-tier
alternative), where DATABASE_URL is already set correctly — never pass a
connection string on the command line or paste it anywhere else.

    python scripts/seed_demo_users.py

Creates one platform-admin account and five plain test accounts, all
pre-verified (bypassing the real email-verification link, which nothing in
this deployment actually delivers — see DEPLOY.md). Safe to re-run: any
email that already exists is left untouched rather than re-created.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config.settings import get_settings
from app.shared.application.seed_demo_data import run_seed
from app.shared.infrastructure.clock import SystemClock
from app.shared.infrastructure.db.session import create_engine, create_session_factory
from app.shared.infrastructure.password_hasher import BcryptPasswordHasher


async def main() -> None:
    engine = create_engine()
    session_factory = create_session_factory(engine)
    settings = get_settings()
    result = await run_seed(
        session_factory,
        BcryptPasswordHasher(),
        SystemClock(),
        admin_password=settings.seed_admin_password,
        user_password=settings.seed_user_password,
    )
    await engine.dispose()

    print(f"Created: {result['created']}")
    print(f"Already existed (left untouched): {result['skipped']}")
    print("Passwords for the accounts created just now (shown once, save them):")
    for email, password in result["credentials"].items():  # type: ignore[union-attr]
        print(f"  {email}  {password}")
    print("All accounts above are now verified and ready to log in.")


if __name__ == "__main__":
    asyncio.run(main())
