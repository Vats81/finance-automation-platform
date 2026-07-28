"""One-time local dev seed: creates demo users across all three roles,
including a Finance Admin — solving the bootstrap chicken-and-egg problem
(role assignment via /users/{id}/role itself requires an existing Finance
Admin). Entra object ids match exactly what the frontend's dev-mode login
generates (`dev-${email}`, see frontend/src/lib/auth/devAuth.ts), so
logging in with one of these emails via the dev-mode login form picks up
the seeded role instead of the default AP_CLERK.

Run: docker compose exec backend python scripts/seed_dev_data.py
"""

import asyncio

from app.bootstrap.container import get_container
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.identity.domain.entities import User
from app.identity.domain.value_objects import EmailAddress, Role

SEED_USERS = [
    ("admin@example.com", "Finance Admin", Role.FINANCE_ADMIN),
    ("approver@example.com", "Sample Approver", Role.APPROVER),
    ("clerk@example.com", "Sample AP Clerk", Role.AP_CLERK),
]


async def seed() -> None:
    container = get_container()
    async with container.session_factory() as session:
        uow = AppUnitOfWork(session)
        for email, display_name, role in SEED_USERS:
            entra_object_id = f"dev-{email}"
            existing = await uow.users.get_by_entra_object_id(entra_object_id)
            if existing is not None:
                print(f"Skipping {email} — already seeded.")
                continue

            user = User(
                entra_object_id=entra_object_id,
                email=EmailAddress(email),
                display_name=display_name,
                role=role,
            )
            uow.users.add(user)
            print(f"Seeded {role.value}: {email}")

        await uow.commit()
    await container.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
