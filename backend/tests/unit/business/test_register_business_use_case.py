import uuid

from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.domain.value_objects import BusinessRole
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


async def test_register_business_creates_business_and_owner_membership() -> None:
    uow = FakeUnitOfWork()
    owner_id = uuid.uuid4()

    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=owner_id, name="Acme Retail")
    )

    assert business.owner_user_id == owner_id
    assert business.onboarding_completed is False

    membership = await uow.business_memberships.get_for_user_and_business(
        user_id=owner_id, business_id=business.id
    )
    assert membership is not None
    assert membership.role == BusinessRole.OWNER
    assert membership.is_active is True


async def test_list_my_businesses_returns_registered_business_with_role() -> None:
    from app.business.application.queries.list_my_businesses import (
        ListMyBusinessesQuery,
        ListMyBusinessesUseCase,
    )

    uow = FakeUnitOfWork()
    owner_id = uuid.uuid4()
    await RegisterBusinessUseCase(uow).execute(RegisterBusinessCommand(owner_user_id=owner_id, name="Acme"))

    views = await ListMyBusinessesUseCase(uow).execute(ListMyBusinessesQuery(user_id=owner_id))

    assert len(views) == 1
    assert views[0].business.name == "Acme"
    assert views[0].role == BusinessRole.OWNER
