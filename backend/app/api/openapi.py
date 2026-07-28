from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def custom_openapi(app: FastAPI) -> dict:
    """Injects the bearer-JWT security scheme so /docs shows an "Authorize"
    button and requests can be tried out with a token acquired via the
    frontend's MSAL login (or the dev-mode static token — see identity/api/security.py).
    """
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title="Finance Automation Platform API",
        version="0.1.0",
        description="Invoice / Accounts Payable Automation — foundation slice.",
        routes=app.routes,
        tags=[
            {"name": "identity", "description": "Current user, role assignment"},
            {"name": "vendors", "description": "Vendor onboarding and management"},
            {"name": "purchase-orders", "description": "Purchase order management"},
            {"name": "invoices", "description": "Invoice submission and 2-way matching"},
            {"name": "approvals", "description": "Multi-step approval workflows"},
            {"name": "payments", "description": "Payment scheduling and status"},
            {"name": "audit", "description": "Append-only audit trail"},
        ],
    )
    schema.setdefault("components", {})["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return app.openapi_schema
