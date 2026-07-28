from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.infrastructure.repository_impl import SqlAlchemyApprovalWorkflowRepository
from app.audit.infrastructure.repository_impl import SqlAlchemyAuditLogRepository
from app.business.infrastructure.repository_impl import (
    SqlAlchemyBusinessMembershipRepository,
    SqlAlchemyBusinessRepository,
)
from app.customers.infrastructure.repository_impl import SqlAlchemyCustomerRepository
from app.expenses.infrastructure.repository_impl import SqlAlchemyExpenseRepository
from app.identity.infrastructure.repository_impl import SqlAlchemyUserRepository
from app.inventory.infrastructure.repository_impl import SqlAlchemyProductRepository
from app.invoices.infrastructure.repository_impl import SqlAlchemyInvoiceRepository
from app.payments.infrastructure.repository_impl import SqlAlchemyPaymentRepository
from app.purchase_orders.infrastructure.repository_impl import SqlAlchemyPurchaseOrderRepository
from app.purchases.infrastructure.repository_impl import SqlAlchemyPurchaseRepository
from app.sales.infrastructure.repository_impl import SqlAlchemySaleRepository
from app.shared.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.vendors.infrastructure.repository_impl import SqlAlchemyVendorRepository


class AppUnitOfWork(SqlAlchemyUnitOfWork):
    """Composition-root Unit of Work: adds one typed repository property per
    bounded context on top of the generic outbox-aware base, as each context
    is built (see app/bootstrap/container.py). This is the only place that
    imports every context's infrastructure package, which is intentional —
    it is the composition root, not the domain/application layer, so it is
    allowed to know about every context.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.users = SqlAlchemyUserRepository(self)
        self.businesses = SqlAlchemyBusinessRepository(self)
        self.business_memberships = SqlAlchemyBusinessMembershipRepository(self)
        self.customers = SqlAlchemyCustomerRepository(self)
        self.sales = SqlAlchemySaleRepository(self)
        self.products = SqlAlchemyProductRepository(self)
        self.expenses = SqlAlchemyExpenseRepository(self)
        self.purchases = SqlAlchemyPurchaseRepository(self)
        self.vendors = SqlAlchemyVendorRepository(self)
        self.purchase_orders = SqlAlchemyPurchaseOrderRepository(self)
        self.invoices = SqlAlchemyInvoiceRepository(self)
        self.approval_workflows = SqlAlchemyApprovalWorkflowRepository(self)
        self.payments = SqlAlchemyPaymentRepository(self)
        self.audit_log = SqlAlchemyAuditLogRepository(self)
