import uuid
from dataclasses import dataclass

from app.customers.application.ports import CustomersUnitOfWork
from app.customers.domain.entities import Customer
from app.customers.domain.exceptions import CustomerNotFoundException


@dataclass(frozen=True)
class GetCustomerQuery:
    business_id: uuid.UUID
    customer_id: uuid.UUID


class GetCustomerUseCase:
    def __init__(self, uow: CustomersUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: GetCustomerQuery) -> Customer:
        customer = await self._uow.customers.get_by_id_for_business(query.customer_id, query.business_id)
        if customer is None:
            raise CustomerNotFoundException(f"Customer {query.customer_id} not found")
        return customer
