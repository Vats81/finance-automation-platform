"""Shared logic for seeding demo/test accounts into a freshly-deployed
environment. Used by both scripts/seed_demo_users.py (local/CLI) and the
/internal/seed-demo-users route (for hosts without shell access, e.g.
Render's free tier) — kept in one place so the two callers can't drift.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.identity.application.commands.register_user import (
    RegisterUserCommand,
    RegisterUserUseCase,
)
from app.identity.domain.exceptions import EmailAlreadyRegisteredException
from app.shared.application.ports import IClock, IPasswordHasher

# email -> (password, display_name, is_platform_admin)
DEMO_USERS: dict[str, tuple[str, str, bool]] = {
    "admin@financeai.app": ("Admin@FinanceAI2026!", "Platform Admin", True),
    "friend1@financeai-test.app": ("Friend1@Test2026!", "Friend One", False),
    "friend2@financeai-test.app": ("Friend2@Test2026!", "Friend Two", False),
    "friend3@financeai-test.app": ("Friend3@Test2026!", "Friend Three", False),
    "friend4@financeai-test.app": ("Friend4@Test2026!", "Friend Four", False),
    "friend5@financeai-test.app": ("Friend5@Test2026!", "Friend Five", False),
}


async def run_seed(
    session_factory: async_sessionmaker,
    password_hasher: IPasswordHasher,
    clock: IClock,
) -> dict[str, list[str]]:
    """Creates every account in DEMO_USERS that doesn't already exist, then
    marks all of them verified (and admin ones as platform admins) via a
    direct SQL update — bypassing the real email-verification link, which
    nothing in this deployment actually delivers. Safe to re-run.
    """
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

    return {"created": created, "skipped": skipped}
