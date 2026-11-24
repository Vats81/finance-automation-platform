"""Real-Postgres test of the WhatsApp summary setting: it persists, and the scheduled job finds the right
businesses. Requires a database (Docker or TEST_DATABASE_URL); skipped otherwise.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.application.commands.complete_onboarding import (
    CompleteOnboardingCommand,
    CompleteOnboardingUseCase,
)
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)

pytestmark = pytest.mark.integration


async def _business(uow: AppUnitOfWork, name: str, frequency: str | None):
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name=name, currency="INR")
    )
    return await CompleteOnboardingUseCase(uow).execute(
        CompleteOnboardingCommand(business_id=business.id, summary_frequency=frequency)
    )


async def test_the_summary_setting_persists_and_the_job_finds_who_asked(db_session: AsyncSession) -> None:
    uow = AppUnitOfWork(db_session)
    daily = await _business(uow, "Daily Co", "daily")
    weekly = await _business(uow, "Weekly Co", "weekly")
    await _business(uow, "Quiet Co", None)

    due = await uow.businesses.list_with_summary_frequency(("daily", "weekly"))

    assert {b.id for b in due} == {daily.id, weekly.id}
    daily.summary_last_sent_on = date(2026, 11, 24)
    await uow.businesses.update(daily)
    await uow.commit()
    db_session.expire_all()
    stored = await uow.businesses.get_by_id(daily.id)
    assert stored is not None
    assert stored.summary_frequency == "daily" and stored.summary_last_sent_on == date(2026, 11, 24)
