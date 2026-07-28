import uuid

from app.admin.application.commands.reactivate_business import (
    ReactivateBusinessCommand,
    ReactivateBusinessUseCase,
)
from app.admin.application.commands.suspend_business import (
    SuspendBusinessCommand,
    SuspendBusinessUseCase,
)
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.domain.value_objects import BusinessStatus
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


async def test_suspend_business_sets_status_suspended() -> None:
    uow = FakeUnitOfWork()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Acme")
    )

    suspended = await SuspendBusinessUseCase(uow).execute(
        SuspendBusinessCommand(business_id=business.id)
    )

    assert suspended.status == BusinessStatus.SUSPENDED


async def test_reactivate_business_sets_status_active() -> None:
    uow = FakeUnitOfWork()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Acme")
    )
    await SuspendBusinessUseCase(uow).execute(SuspendBusinessCommand(business_id=business.id))

    reactivated = await ReactivateBusinessUseCase(uow).execute(
        ReactivateBusinessCommand(business_id=business.id)
    )

    assert reactivated.status == BusinessStatus.ACTIVE
