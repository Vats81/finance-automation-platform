"""Creates (or promotes) the platform admin on an email address you own, and retires the seeded demo admin.

The seed script created `admin@financeai.app`, an address on a domain nobody here controls. Its
password-reset emails would go to whoever owns that domain, so replace it with a real address:

    set DATABASE_URL=<your database connection string>      (never type it into a chat or a file)
    set ADMIN_EMAIL=admin@finverlo.com
    set ADMIN_PASSWORD=<a new strong password>              (or leave unset to be prompted)
    python scripts/create_platform_admin.py                 (create or promote, keep the old admin)
    python scripts/create_platform_admin.py --retire-seeded (also switch off admin@financeai.app)
    python scripts/create_platform_admin.py --set-password  (set a new password on the existing admin)

Run it from the backend folder. It makes the account verified and a platform admin, so you can sign
in at /app/login and open /admin. With --retire-seeded the seeded admin loses admin rights, is made
inactive and has its password removed; it can then be deleted from Admin -> Users, or by
purge_qa_data.py, which also removes the seeded friend accounts. The password is never printed.
"""

import argparse
import asyncio
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.bootstrap.unit_of_work import AppUnitOfWork  # noqa: E402
from app.identity.application.commands.register_user import (  # noqa: E402
    RegisterUserCommand,
    RegisterUserUseCase,
)
from app.identity.domain.exceptions import EmailAlreadyRegisteredException  # noqa: E402
from app.shared.infrastructure.clock import SystemClock  # noqa: E402
from app.shared.infrastructure.db.session import create_engine, create_session_factory  # noqa: E402
from app.shared.infrastructure.password_hasher import BcryptPasswordHasher  # noqa: E402

SEEDED_ADMIN = "admin@financeai.app"


async def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--retire-seeded", action="store_true", help=f"switch off {SEEDED_ADMIN}")
    parser.add_argument(
        "--set-password",
        action="store_true",
        help="also set this password on an account that already exists (for a forgotten or mistyped one)",
    )
    args = parser.parse_args()

    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    if not os.environ.get("DATABASE_URL") or not email:
        print("Set DATABASE_URL and ADMIN_EMAIL in the environment first (see the top of this file).")
        return 2
    if email == SEEDED_ADMIN:
        print(f"Use a real address you own, not {SEEDED_ADMIN}.")
        return 2
    password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("New admin password (hidden): ")
    if not os.environ.get("ADMIN_PASSWORD") and getpass.getpass("Type it again to confirm: ") != password:
        print("The two entries did not match, so nothing was changed. Run it again.")
        return 2
    if len(password) < 12:
        print("Use a password of at least 12 characters.")
        return 2

    engine = create_engine()
    session_factory = create_session_factory(engine)
    created = False
    async with session_factory() as session:
        try:
            await RegisterUserUseCase(AppUnitOfWork(session), BcryptPasswordHasher(), SystemClock()).execute(
                RegisterUserCommand(email=email, password=password, display_name="Platform Admin")
            )
            created = True
        except EmailAlreadyRegisteredException:
            pass

    async with session_factory() as session:
        await session.execute(
            text(
                "UPDATE users SET is_email_verified = true, is_platform_admin = true, is_active = true WHERE email = :e"
            ),
            {"e": email},
        )
        if args.set_password:
            await session.execute(
                text("UPDATE users SET password_hash = :h WHERE email = :e"),
                {"h": BcryptPasswordHasher().hash(password), "e": email},
            )
        if args.retire_seeded:
            await session.execute(
                text(
                    "UPDATE users SET is_platform_admin = false, is_active = false, password_hash = NULL "
                    "WHERE email = :e"
                ),
                {"e": SEEDED_ADMIN},
            )
        await session.commit()
    await engine.dispose()

    print(
        f"{'Created' if created else 'Promoted existing account'}: {email} is now a verified platform admin."
    )
    if not created and args.set_password:
        print("Its password has been set to the one you just entered.")
    elif not created:
        print(
            "Its password was NOT changed (an existing account keeps its own). Add --set-password to change it."
        )
    if args.retire_seeded:
        print(f"{SEEDED_ADMIN} has been switched off. Delete it from Admin -> Users when you are signed in.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
