"""Shared logic for seeding demo/test accounts into a freshly-deployed
environment. Used by both scripts/seed_demo_users.py (local/CLI) and the
/internal/seed-demo-users route (for hosts without shell access, e.g.
Render's free tier) — kept in one place so the two callers can't drift.

No password lives in this file. This repository is public, and the accounts
seeded here exist on the live deployment (one of them is the platform
admin), so a password written down here is a password anyone can use.
Passwords come from SEED_ADMIN_PASSWORD / SEED_USER_PASSWORD when set, and
are otherwise generated randomly; either way they're handed back once, to
whoever ran the seed, and never stored in plain text.
"""

import secrets

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.identity.application.commands.register_user import (
    RegisterUserCommand,
    RegisterUserUseCase,
)
from app.identity.domain.exceptions import EmailAlreadyRegisteredException
from app.shared.application.ports import IClock, IPasswordHasher

# email -> (display_name, is_platform_admin)
DEMO_USERS: dict[str, tuple[str, bool]] = {
    "admin@financeai.app": ("Platform Admin", True),
    "friend1@financeai-test.app": ("Friend One", False),
    "friend2@financeai-test.app": ("Friend Two", False),
    "friend3@financeai-test.app": ("Friend Three", False),
    "friend4@financeai-test.app": ("Friend Four", False),
    "friend5@financeai-test.app": ("Friend Five", False),
}


def build_credentials(*, admin_password: str = "", user_password: str = "") -> dict[str, str]:
    """A password for every demo account: the configured one for its kind if
    set (a single shared value for all the friend accounts), otherwise a
    fresh random one per account.
    """
    credentials: dict[str, str] = {}
    for email, (_, is_admin) in DEMO_USERS.items():
        configured = admin_password if is_admin else user_password
        credentials[email] = configured or secrets.token_urlsafe(14)
    return credentials


async def run_seed(
    session_factory: async_sessionmaker,
    password_hasher: IPasswordHasher,
    clock: IClock,
    *,
    admin_password: str = "",
    user_password: str = "",
) -> dict[str, object]:
    """Creates every account in DEMO_USERS that doesn't already exist, then
    marks all of them verified (and admin ones as platform admins) via a
    direct SQL update — bypassing the real email-verification link, which
    nothing in this deployment actually delivers. Safe to re-run.

    Returns the emails created and skipped, plus `credentials`: the password
    of each account that was *created* this run (accounts that already
    existed keep whatever password they have, which isn't known here).
    """
    passwords = build_credentials(admin_password=admin_password, user_password=user_password)
    created: list[str] = []
    skipped: list[str] = []

    for email, (display_name, _is_admin) in DEMO_USERS.items():
        async with session_factory() as session:
            uow = AppUnitOfWork(session)
            use_case = RegisterUserUseCase(uow, password_hasher, clock)
            try:
                await use_case.execute(
                    RegisterUserCommand(email=email, password=passwords[email], display_name=display_name)
                )
                created.append(email)
            except EmailAlreadyRegisteredException:
                skipped.append(email)

    admin_emails = [email for email, (_, is_admin) in DEMO_USERS.items() if is_admin]
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

    return {
        "created": created,
        "skipped": skipped,
        "credentials": {email: passwords[email] for email in created},
    }
