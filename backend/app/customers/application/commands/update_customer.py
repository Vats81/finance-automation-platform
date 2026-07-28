import uuid
from dataclasses import dataclass

from app.customers.application.ports import CustomersUnitOfWork
from app.customers.domain.entities import Customer
from app.customers.domain.exceptions import CustomerNotFoundException
from app.customers.domain.value_objects import CustomerAddress, CustomerEmailAddress


@dataclass(frozen=True)
class UpdateCustomerCommand:
    business_id: uuid.UUID
    customer_id: uuid.UUID
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    street: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    gst_number: str | None = None


class UpdateCustomerUseCase:
    def __init__(self, uow: CustomersUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: UpdateCustomerCommand) -> Customer:
        customer = await self._uow.customers.get_by_id_for_business(command.customer_id, command.business_id)
        if customer is None:
            raise CustomerNotFoundException(f"Customer {command.customer_id} not found")

        address = None
        if any([command.street, command.city, command.state, command.postal_code]):
            base = customer.address
            address = CustomerAddress(
                street=command.street or (base.street if base else ""),
                city=command.city or (base.city if base else ""),
                state=command.state or (base.state if base else ""),
                postal_code=command.postal_code or (base.postal_code if base else ""),
                country=command.country or (base.country if base else "US"),
            )

        customer.update_details(
            name=command.name,
            phone=command.phone,
            email=CustomerEmailAddress(command.email) if command.email else None,
            address=address,
            gst_number=command.gst_number,
        )
        await self._uow.customers.update(customer)
        await self._uow.commit()
        return customer
