"""Real app + real Postgres — verifies the auth boundary end-to-end: no
token, malformed token, and a valid dev-mode token JIT-provisioning a user.
Requires Docker; skipped automatically otherwise.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header

pytestmark = pytest.mark.integration


async def test_request_without_token_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/api/v1/me")

    assert response.status_code == 403  # HTTPBearer(auto_error=True) rejects a missing header


async def test_request_with_malformed_token_is_unauthorized(client: AsyncClient) -> None:
    response = await client.get("/api/v1/me", headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 401
    assert response.json()["error_code"] == "invalid_token"


async def test_valid_dev_token_jit_provisions_user(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/me", headers=auth_header(oid="new-user-oid", email="new.user@example.com", name="New User")
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "new.user@example.com"
    assert body["display_name"] == "New User"
    assert body["role"] == "ap_clerk"  # default role for first-seen login


async def test_same_oid_reuses_the_same_provisioned_user(client: AsyncClient) -> None:
    first = await client.get("/api/v1/me", headers=auth_header(oid="stable-oid", email="stable@example.com"))
    second = await client.get("/api/v1/me", headers=auth_header(oid="stable-oid", email="stable@example.com"))

    assert first.json()["id"] == second.json()["id"]


async def test_finance_admin_only_endpoint_rejects_ap_clerk(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/users", headers=auth_header(oid="regular-clerk", email="clerk@example.com")
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "unauthorized_action"
