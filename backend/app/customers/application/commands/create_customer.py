import uuid
from dataclasses import dataclass

from app.customers.application.ports import CustomersUnitOfWork
from app.customers.domain.entities import Customer
from app.customers.domain.value_objects import CustomerAddress, CustomerEmailAddress


@dataclass(frozen=True)
class CreateCustomerCommand:
    business_id: uuid.UUID
    name: str
    phone: str | None = None
    email: str | None = None
    street: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str = "US"
    gst_number: str | None = None


class CreateCustomerUseCase:
    def __init__(self, uow: CustomersUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: CreateCustomerCommand) -> Customer:
        address = None
        if command.street and command.city and command.state and command.postal_code:
            address = CustomerAddress(
                street=command.street,
                city=command.city,
                state=command.state,
                postal_code=command.postal_code,
                country=command.country,
            )

        customer = Customer.create(
            business_id=command.business_id,
            name=command.name,
            phone=command.phone,
            email=CustomerEmailAddress(command.email) if command.email else None,
            address=address,
            gst_number=command.gst_number,
        )
        self._uow.customers.add(customer)
        await self._uow.commit()
        return customer
