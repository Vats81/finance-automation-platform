import uuid

from app.business.domain.entities import Business, BusinessMembership
from app.business.domain.repository import IBusinessMembershipRepository, IBusinessRepository
from app.customers.domain.entities import Customer
from app.customers.domain.repository import ICustomerRepository
from app.expenses.domain.entities import Expense
from app.expenses.domain.repository import IExpenseRepository
from app.identity.domain.entities import User
from app.identity.domain.repository import IUserRepository
from app.inventory.domain.entities import Product
from app.inventory.domain.repository import IProductRepository
from app.invoices.domain.entities import Invoice
from app.invoices.domain.repository import IInvoiceRepository
from app.purchase_orders.domain.entities import PurchaseOrder
from app.purchase_orders.domain.repository import IPurchaseOrderRepository
from app.purchases.domain.entities import Purchase
from app.purchases.domain.repository import IPurchaseRepository
from app.sales.domain.entities import Sale
from app.sales.domain.repository import ISaleRepository
from app.shared.application.unit_of_work import IUnitOfWork
from app.vendors.domain.entities import Vendor
from app.vendors.domain.repository import IVendorRepository


class FakeUserRepository(IUserRepository):
    def __init__(self) -> None:
        self._store: dict[uuid.UUID, User] = {}

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self._store.get(user_id)

    async def get_by_entra_object_id(self, entra_object_id: str) -> User | None:
        return next((u for u in self._store.values() if u.entra_object_id == entra_object_id), None)

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._store.values() if str(u.email) == email), None)

    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[User], int]:
        items = list(self._store.values())
        return items[offset : offset + limit], len(items)

    def add(self, user: User) -> None:
        self._store[user.id] = user
        user.pull_domain_events()

    async def update(self, user: User) -> None:
        self._store[user.id] = user
        user.pull_domain_events()


class FakeBusinessRepository(IBusinessRepository):
    def __init__(self) -> None:
        self._store: dict[uuid.UUID, Business] = {}

    async def get_by_id(self, business_id: uuid.UUID) -> Business | None:
        return self._store.get(business_id)

    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[Business], int]:
        items = sorted(self._store.values(), key=lambda b: b.created_at, reverse=True)
        return items[offset : offset + limit], len(items)

    def add(self, business: Business) -> None:
        self._store[business.id] = business
        business.pull_domain_events()

    async def update(self, business: Business) -> None:
        self._store[business.id] = business
        business.pull_domain_events()


class FakeBusinessMembershipRepository(IBusinessMembershipRepository):
    def __init__(self) -> None:
        self._store: dict[uuid.UUID, BusinessMembership] = {}

    async def get_by_id(self, membership_id: uuid.UUID) -> BusinessMembership | None:
        return self._store.get(membership_id)

    async def get_for_user_and_business(
        self, *, user_id: uuid.UUID, business_id: uuid.UUID
    ) -> BusinessMembership | None:
        return next(
            (
                m
                for m in self._store.values()
                if m.user_id == user_id and m.business_id == business_id
            ),
            None,
        )

    async def list_for_user(self, user_id: uuid.UUID) -> list[BusinessMembership]:
        return [m for m in self._store.values() if m.user_id == user_id]

    async def list_for_business(self, business_id: uuid.UUID) -> list[BusinessMembership]:
        return [m for m in self._store.values() if m.business_id == business_id]

    def add(self, membership: BusinessMembership) -> None:
        self._store[membership.id] = membership
        membership.pull_domain_events()

    async def update(self, membership: BusinessMembership) -> None:
        self._store[membership.id] = membership
        membership.pull_domain_events()


class FakeVendorRepository(IVendorRepository):
    def __init__(self) -> None:
        self._store: dict[uuid.UUID, Vendor] = {}

    async def get_by_id(self, vendor_id: uuid.UUID) -> Vendor | None:
        return self._store.get(vendor_id)

    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[Vendor], int]:
        items = list(self._store.values())
        return items[offset : offset + limit], len(items)

    async def get_by_id_for_business(self, vendor_id: uuid.UUID, business_id: uuid.UUID) -> Vendor | None:
        vendor = self._store.get(vendor_id)
        return vendor if vendor is not None and vendor.business_id == business_id else None

    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Vendor], int]:
        items = [v for v in self._store.values() if v.business_id == business_id]
        return items[offset : offset + limit], len(items)

    def add(self, vendor: Vendor) -> None:
        self._store[vendor.id] = vendor
        vendor.pull_domain_events()

    async def update(self, vendor: Vendor) -> None:
        self._store[vendor.id] = vendor
        vendor.pull_domain_events()


class FakePurchaseOrderRepository(IPurchaseOrderRepository):
    def __init__(self) -> None:
        self._store: dict[uuid.UUID, PurchaseOrder] = {}

    async def get_by_id(self, po_id: uuid.UUID) -> PurchaseOrder | None:
        return self._store.get(po_id)

    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[PurchaseOrder], int]:
        items = list(self._store.values())
        return items[offset : offset + limit], len(items)

    def add(self, purchase_order: PurchaseOrder) -> None:
        self._store[purchase_order.id] = purchase_order
        purchase_order.pull_domain_events()

    async def update(self, purchase_order: PurchaseOrder) -> None:
        self._store[purchase_order.id] = purchase_order
        purchase_order.pull_domain_events()


class FakeInvoiceRepository(IInvoiceRepository):
    def __init__(self) -> None:
        self._store: dict[uuid.UUID, Invoice] = {}

    async def get_by_id(self, invoice_id: uuid.UUID) -> Invoice | None:
        return self._store.get(invoice_id)

    async def list_all(self, *, offset: int = 0, limit: int = 50) -> tuple[list[Invoice], int]:
        items = list(self._store.values())
        return items[offset : offset + limit], len(items)

    def add(self, invoice: Invoice) -> None:
        self._store[invoice.id] = invoice
        invoice.pull_domain_events()

    async def update(self, invoice: Invoice) -> None:
        self._store[invoice.id] = invoice
        invoice.pull_domain_events()


class FakeCustomerRepository(ICustomerRepository):
    def __init__(self) -> None:
        self._store: dict[uuid.UUID, Customer] = {}

    async def get_by_id_for_business(self, customer_id: uuid.UUID, business_id: uuid.UUID) -> Customer | None:
        customer = self._store.get(customer_id)
        return customer if customer is not None and customer.business_id == business_id else None

    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Customer], int]:
        items = [c for c in self._store.values() if c.business_id == business_id]
        return items[offset : offset + limit], len(items)

    def add(self, customer: Customer) -> None:
        self._store[customer.id] = customer
        customer.pull_domain_events()

    async def update(self, customer: Customer) -> None:
        self._store[customer.id] = customer
        customer.pull_domain_events()


class FakeSaleRepository(ISaleRepository):
    def __init__(self) -> None:
        self._store: dict[uuid.UUID, Sale] = {}

    async def get_by_id_for_business(self, sale_id: uuid.UUID, business_id: uuid.UUID) -> Sale | None:
        sale = self._store.get(sale_id)
        return sale if sale is not None and sale.business_id == business_id else None

    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Sale], int]:
        items = [s for s in self._store.values() if s.business_id == business_id]
        return items[offset : offset + limit], len(items)

    def add(self, sale: Sale) -> None:
        self._store[sale.id] = sale
        sale.pull_domain_events()

    async def update(self, sale: Sale) -> None:
        self._store[sale.id] = sale
        sale.pull_domain_events()


class FakeProductRepository(IProductRepository):
    def __init__(self) -> None:
        self._store: dict[uuid.UUID, Product] = {}

    async def get_by_id_for_business(self, product_id: uuid.UUID, business_id: uuid.UUID) -> Product | None:
        product = self._store.get(product_id)
        return product if product is not None and product.business_id == business_id else None

    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Product], int]:
        items = [p for p in self._store.values() if p.business_id == business_id]
        return items[offset : offset + limit], len(items)

    def add(self, product: Product) -> None:
        self._store[product.id] = product
        product.pull_domain_events()

    async def update(self, product: Product) -> None:
        self._store[product.id] = product
        product.pull_domain_events()


class FakeExpenseRepository(IExpenseRepository):
    def __init__(self) -> None:
        self._store: dict[uuid.UUID, Expense] = {}

    async def get_by_id_for_business(self, expense_id: uuid.UUID, business_id: uuid.UUID) -> Expense | None:
        expense = self._store.get(expense_id)
        return expense if expense is not None and expense.business_id == business_id else None

    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Expense], int]:
        items = [e for e in self._store.values() if e.business_id == business_id]
        return items[offset : offset + limit], len(items)

    def add(self, expense: Expense) -> None:
        self._store[expense.id] = expense
        expense.pull_domain_events()

    async def update(self, expense: Expense) -> None:
        self._store[expense.id] = expense
        expense.pull_domain_events()


class FakePurchaseRepository(IPurchaseRepository):
    def __init__(self) -> None:
        self._store: dict[uuid.UUID, Purchase] = {}

    async def get_by_id_for_business(self, purchase_id: uuid.UUID, business_id: uuid.UUID) -> Purchase | None:
        purchase = self._store.get(purchase_id)
        return purchase if purchase is not None and purchase.business_id == business_id else None

    async def list_for_business(
        self, business_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Purchase], int]:
        items = [p for p in self._store.values() if p.business_id == business_id]
        return items[offset : offset + limit], len(items)

    def add(self, purchase: Purchase) -> None:
        self._store[purchase.id] = purchase
        purchase.pull_domain_events()

    async def update(self, purchase: Purchase) -> None:
        self._store[purchase.id] = purchase
        purchase.pull_domain_events()


class FakeUnitOfWork(IUnitOfWork):
    """In-memory UoW for application-layer tests that don't need a real
    database — repos hold references directly rather than going through a
    session, and commit()/rollback() are no-ops since there's no
    transaction to manage. Domain events are dropped (pulled and discarded)
    on add/update, mirroring what the outbox write would otherwise consume.
    """

    def __init__(self) -> None:
        self.vendors = FakeVendorRepository()
        self.purchase_orders = FakePurchaseOrderRepository()
        self.invoices = FakeInvoiceRepository()
        self.users = FakeUserRepository()
        self.businesses = FakeBusinessRepository()
        self.business_memberships = FakeBusinessMembershipRepository()
        self.customers = FakeCustomerRepository()
        self.sales = FakeSaleRepository()
        self.products = FakeProductRepository()
        self.expenses = FakeExpenseRepository()
        self.purchases = FakePurchaseRepository()

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass
