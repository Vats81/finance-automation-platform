"""Real-Postgres check for SqlAlchemyContactRequestStore — the server-side
created_at default, the commit-before-return behaviour the use case relies
on, and the notified flag update are exactly what an in-memory fake can't
prove. Requires Docker; skipped automatically otherwise (see
tests/conftest.py:docker_available).
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.contact.infrastructure.store_impl import SqlAlchemyContactRequestStore

pytestmark = pytest.mark.integration


async def test_contact_request_round_trips_through_postgres(db_session: AsyncSession) -> None:
    store = SqlAlchemyContactRequestStore(db_session)

    saved = await store.add(name="Asha Rao", email="asha@example.com", business_name=None, message="Demo?")

    assert saved.notified is False
    assert saved.created_at is not None  # filled by the server default

    await store.mark_notified(saved.id)
    recent = await store.list_recent(limit=10)

    assert [r.id for r in recent] == [saved.id]
    assert recent[0].notified is True
    assert recent[0].business_name is None
    assert recent[0].message == "Demo?"
