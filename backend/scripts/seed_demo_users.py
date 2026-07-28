"""One-time seed script for a freshly-deployed environment.

Run this from the deployed backend's own shell (e.g. Render's "Shell" tab),
where DATABASE_URL is already set correctly — never pass a connection
string on the command line or paste it anywhere else.

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

from sqlalchemy import text

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.identity.application.commands.register_user import (
    RegisterUserCommand,
    RegisterUserUseCase,
)
from app.identity.domain.exceptions import EmailAlreadyRegisteredException
from app.shared.infrastructure.clock import SystemClock
from app.shared.infrastructure.db.session import create_engine, create_session_factory
from app.shared.infrastructure.password_hasher import BcryptPasswordHasher

# email -> (password, display_name, is_platform_admin)
DEMO_USERS: dict[str, tuple[str, str, bool]] = {
    "admin@financeai.app": ("Admin@FinanceAI2026!", "Platform Admin", True),
    "friend1@financeai-test.app": ("Friend1@Test2026!", "Friend One", False),
    "friend2@financeai-test.app": ("Friend2@Test2026!", "Friend Two", False),
    "friend3@financeai-test.app": ("Friend3@Test2026!", "Friend Three", False),
    "friend4@financeai-test.app": ("Friend4@Test2026!", "Friend Four", False),
    "friend5@financeai-test.app": ("Friend5@Test2026!", "Friend Five", False),
}


async def main() -> None:
    engine = create_engine()
    session_factory = create_session_factory(engine)
    password_hasher = BcryptPasswordHasher()
    clock = SystemClock()

    created: list[str] = []
    skipped: list[str] = []

    for email, (password, display_name, _is_admin) in DEMO_USERS.items():
        async with session_factory() as session:
            uow = AppUnitOfWork(session)
            use_case = RegisterUserUseCase(uow, password_hasher, clock)
            try:
                await use_case.execute(
                    RegisterUserCommand(email=email, password=password, display_name=display_name)
                )
                created.append(email)
            except EmailAlreadyRegisteredException:
                skipped.append(email)

    admin_emails = [email for email, (_, _, is_admin) in DEMO_USERS.items() if is_admin]
    async with session_factory() as session:
        await session.execute(
            text("UPDATE users SET is_email_verified = true WHERE email = ANY(:emails)"),
            {"emails": list(DEMO_USERS.keys())},
        )
        if admin_emails:
            await session.execute(
                text("UPDATE users SET is_platform_admin = true WHERE email = ANY(:emails)"),
                {"emails": admin_emails},
            )
        await session.commit()

    await engine.dispose()

    print(f"Created: {created}")
    print(f"Already existed (left untouched): {skipped}")
    print("All accounts above are now verified and ready to log in.")


if __name__ == "__main__":
    asyncio.run(main())
