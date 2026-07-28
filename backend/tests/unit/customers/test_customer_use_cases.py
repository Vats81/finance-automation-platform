import uuid

import pytest

from app.customers.application.commands.create_customer import CreateCustomerCommand, CreateCustomerUseCase
from app.customers.application.commands.deactivate_customer import (
    DeactivateCustomerCommand,
    DeactivateCustomerUseCase,
)
from app.customers.application.commands.reactivate_customer import (
    ReactivateCustomerCommand,
    ReactivateCustomerUseCase,
)
from app.customers.application.commands.update_customer import UpdateCustomerCommand, UpdateCustomerUseCase
from app.customers.application.queries.get_customer import GetCustomerQuery, GetCustomerUseCase
from app.customers.application.queries.list_customers import ListCustomersQuery, ListCustomersUseCase
from app.customers.domain.exceptions import CustomerNotFoundException
from app.customers.domain.value_objects import CustomerStatus
from app.shared.application.pagination import PageRequest
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


async def test_create_and_get_customer() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    created = await CreateCustomerUseCase(uow).execute(
        CreateCustomerCommand(business_id=business_id, name="Jane's Diner", email="jane@example.com")
    )

    fetched = await GetCustomerUseCase(uow).execute(
        GetCustomerQuery(business_id=business_id, customer_id=created.id)
    )
    assert fetched.name == "Jane's Diner"
    assert fetched.status == CustomerStatus.ACTIVE


async def test_get_customer_from_wrong_business_raises_not_found() -> None:
    uow = FakeUnitOfWork()
    customer = await CreateCustomerUseCase(uow).execute(
        CreateCustomerCommand(business_id=uuid.uuid4(), name="Jane's Diner")
    )

    with pytest.raises(CustomerNotFoundException):
        await GetCustomerUseCase(uow).execute(
            GetCustomerQuery(business_id=uuid.uuid4(), customer_id=customer.id)
        )


async def test_list_customers_is_scoped_per_business() -> None:
    uow = FakeUnitOfWork()
    business_a = uuid.uuid4()
    business_b = uuid.uuid4()
    await CreateCustomerUseCase(uow).execute(CreateCustomerCommand(business_id=business_a, name="A Customer"))
    await CreateCustomerUseCase(uow).execute(CreateCustomerCommand(business_id=business_b, name="B Customer"))

    page = await ListCustomersUseCase(uow).execute(
        ListCustomersQuery(business_id=business_a, page=PageRequest())
    )

    assert page.total == 1
    assert page.items[0].name == "A Customer"


async def test_update_customer() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    customer = await CreateCustomerUseCase(uow).execute(
        CreateCustomerCommand(business_id=business_id, name="Jane's Diner")
    )

    updated = await UpdateCustomerUseCase(uow).execute(
        UpdateCustomerCommand(business_id=business_id, customer_id=customer.id, phone="555-0100")
    )

    assert updated.phone == "555-0100"


async def test_deactivate_customer() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    customer = await CreateCustomerUseCase(uow).execute(
        CreateCustomerCommand(business_id=business_id, name="Jane's Diner")
    )

    deactivated = await DeactivateCustomerUseCase(uow).execute(
        DeactivateCustomerCommand(business_id=business_id, customer_id=customer.id)
    )

    assert deactivated.status == CustomerStatus.INACTIVE


async def test_reactivate_customer() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    customer = await CreateCustomerUseCase(uow).execute(
        CreateCustomerCommand(business_id=business_id, name="Jane's Diner")
    )
    await DeactivateCustomerUseCase(uow).execute(
        DeactivateCustomerCommand(business_id=business_id, customer_id=customer.id)
    )

    reactivated = await ReactivateCustomerUseCase(uow).execute(
        ReactivateCustomerCommand(business_id=business_id, customer_id=customer.id)
    )

    assert reactivated.status == CustomerStatus.ACTIVE
