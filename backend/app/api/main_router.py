from fastapi import APIRouter

# Each bounded context registers its router here as it is built. Kept as a
# single composition point so app_factory.py never needs to know about
# individual contexts.
api_router = APIRouter(prefix="/api/v1")


def include_context_routers() -> None:
    from app.admin.api.routes import router as admin_router
    from app.ai_assistant.api.routes import router as ai_assistant_router
    from app.approvals.api.routes import router as approvals_router
    from app.audit.api.routes import router as audit_router
    from app.business.api.routes import router as business_router
    from app.business.api.team_member_routes import router as team_member_router
    from app.customers.api.routes import router as customers_router
    from app.dashboard.api.routes import router as dashboard_router
    from app.data_import.api.routes import router as data_import_router
    from app.expenses.api.routes import router as expenses_router
    from app.identity.api.auth_routes import router as auth_router
    from app.identity.api.routes import router as identity_router
    from app.integrations.api.routes import router as integrations_router
    from app.inventory.api.routes import router as inventory_router
    from app.invoices.api.routes import router as invoices_router
    from app.notifications.api.routes import router as notifications_router
    from app.payments.api.routes import router as payments_router
    from app.purchase_orders.api.routes import router as purchase_orders_router
    from app.purchases.api.routes import router as purchases_router
    from app.sales.api.routes import router as sales_router
    from app.vendors.api.business_routes import router as business_vendors_router
    from app.vendors.api.routes import router as vendors_router

    api_router.include_router(identity_router)
    api_router.include_router(auth_router)
    api_router.include_router(admin_router)
    api_router.include_router(ai_assistant_router)
    api_router.include_router(business_router)
    api_router.include_router(team_member_router)
    api_router.include_router(customers_router)
    api_router.include_router(dashboard_router)
    api_router.include_router(data_import_router)
    api_router.include_router(notifications_router)
    api_router.include_router(integrations_router)
    api_router.include_router(expenses_router)
    api_router.include_router(sales_router)
    api_router.include_router(inventory_router)
    api_router.include_router(purchases_router)
    api_router.include_router(vendors_router)
    api_router.include_router(business_vendors_router)
    api_router.include_router(purchase_orders_router)
    api_router.include_router(invoices_router)
    api_router.include_router(approvals_router)
    api_router.include_router(payments_router)
    api_router.include_router(audit_router)


include_context_routers()
