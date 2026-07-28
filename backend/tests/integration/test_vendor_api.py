"""Full-stack test: real FastAPI app + real Postgres (via testcontainers),
routed through actual HTTP calls rather than calling use cases directly —
exercises routing, auth, RBAC, request validation, and the SQLAlchemy
repository/mapper layer together. Requires Docker; skipped automatically
otherwise (see tests/conftest.py:docker_available).
"""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header

pytestmark = pytest.mark.integration


async def test_create_and_get_vendor(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/vendors",
        json={
            "legal_name": "Acme Supplies",
            "contact_email": "ap@acme.com",
            "tax_id": "12-3456789",
            "address": {
                "street": "1 Main St",
                "city": "Springfield",
                "state": "IL",
                "postal_code": "62701",
                "country": "US",
            },
        },
        headers=auth_header(oid="clerk-1", email="clerk@example.com"),
    )

    assert response.status_code == 201, response.text
    vendor = response.json()
    assert vendor["legal_name"] == "Acme Supplies"
    assert vendor["status"] == "pending_review"
    assert vendor["has_w9_on_file"] is False

    get_response = await client.get(
        f"/api/v1/vendors/{vendor['id']}", headers=auth_header(oid="clerk-1", email="clerk@example.com")
    )
    assert get_response.status_code == 200
    assert get_response.json()["id"] == vendor["id"]


async def test_activate_without_w9_returns_422(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/vendors",
        json={
            "legal_name": "No W9 Co",
            "contact_email": "ap@no-w9.com",
            "tax_id": "98-7654321",
            "address": {"street": "1 St", "city": "City", "state": "ST", "postal_code": "00000"},
        },
        headers=auth_header(oid="clerk-2", email="clerk2@example.com"),
    )
    vendor_id = create_response.json()["id"]

    activate_response = await client.post(
        f"/api/v1/vendors/{vendor_id}/activate",
        headers=auth_header(oid="clerk-2", email="clerk2@example.com"),
    )

    assert activate_response.status_code == 422
    assert activate_response.json()["error_code"] == "vendor_missing_w9"


async def test_list_vendors_is_paginated(client: AsyncClient) -> None:
    headers = auth_header(oid="clerk-3", email="clerk3@example.com")
    for i in range(3):
        await client.post(
            "/api/v1/vendors",
            json={
                "legal_name": f"Vendor {i}",
                "contact_email": f"ap{i}@example.com",
                "tax_id": "11-1111111",
                "address": {"street": "1 St", "city": "City", "state": "ST", "postal_code": "00000"},
            },
            headers=headers,
        )

    response = await client.get("/api/v1/vendors?limit=2", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 2
    assert len(body["items"]) == 2
    assert body["total"] >= 3
