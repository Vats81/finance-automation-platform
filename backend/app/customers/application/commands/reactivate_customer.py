import uuid
from dataclasses import dataclass

from app.customers.application.ports import CustomersUnitOfWork
from app.customers.domain.entities import Customer
from app.customers.domain.exceptions import CustomerNotFoundException


@dataclass(frozen=True)
class ReactivateCustomerCommand:
    business_id: uuid.UUID
    customer_id: uuid.UUID


class ReactivateCustomerUseCase:
    def __init__(self, uow: CustomersUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: ReactivateCustomerCommand) -> Customer:
        customer = await self._uow.customers.get_by_id_for_business(command.customer_id, command.business_id)
        if customer is None:
            raise CustomerNotFoundException(f"Customer {command.customer_id} not found")

        customer.reactivate()
        await self._uow.customers.update(customer)
        await self._uow.commit()
        return customer
