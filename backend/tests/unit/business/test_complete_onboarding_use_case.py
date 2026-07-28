import uuid

import pytest

from app.business.application.commands.complete_onboarding import (
    CompleteOnboardingCommand,
    CompleteOnboardingUseCase,
)
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.domain.exceptions import BusinessNotFoundException
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


async def test_complete_onboarding_updates_only_provided_fields() -> None:
    uow = FakeUnitOfWork()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Acme Retail")
    )

    updated = await CompleteOnboardingUseCase(uow).execute(
        CompleteOnboardingCommand(
            business_id=business.id,
            business_type="Retail",
            country="US",
            currency="USD",
            number_of_branches=3,
        )
    )

    assert updated.onboarding_completed is True
    assert updated.business_type == "Retail"
    assert updated.number_of_branches == 3
    assert updated.industry is None  # untouched field stays None


async def test_complete_onboarding_for_unknown_business_raises() -> None:
    uow = FakeUnitOfWork()

    with pytest.raises(BusinessNotFoundException):
        await CompleteOnboardingUseCase(uow).execute(CompleteOnboardingCommand(business_id=uuid.uuid4()))
