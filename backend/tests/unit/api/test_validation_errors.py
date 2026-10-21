"""Regression tests for validation errors on money fields.

Pydantic's error details for a violated Decimal constraint contain a Decimal
(e.g. ctx={'ge': Decimal('0')}). The 422 handler put those details straight
into a JSONResponse, which cannot serialise a Decimal, so the *error
response itself* crashed and the client got a 500. Every money-range
violation in the app (a negative expense, a negative payment, ...) was a
500 instead of a clear "this field must be >= 0". Found by a live QA pass.
"""

from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.api.exception_handlers import register_exception_handlers


class _Body(BaseModel):
    amount: Decimal = Field(ge=0)
    quantity: Decimal = Field(gt=0)
    note: str = Field(max_length=5)


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/things")
    async def create(body: _Body) -> dict[str, str]:
        return {"ok": "yes"}

    return TestClient(app, raise_server_exceptions=False)


def test_a_negative_amount_is_a_422_with_details_not_a_500(client: TestClient) -> None:
    response = client.post("/things", json={"amount": "-50.00", "quantity": "1", "note": "ok"})

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "request_validation_error"
    error = body["errors"][0]
    assert error["loc"] == ["body", "amount"]
    # The constraint (a Decimal in pydantic's details) comes back as plain JSON.
    assert Decimal(str(error["ctx"]["ge"])) == 0


def test_zero_quantity_violating_gt_is_a_422(client: TestClient) -> None:
    response = client.post("/things", json={"amount": "1", "quantity": "0", "note": "ok"})

    assert response.status_code == 422
    assert response.json()["errors"][0]["loc"] == ["body", "quantity"]


def test_several_violations_are_reported_together(client: TestClient) -> None:
    response = client.post("/things", json={"amount": "-1", "quantity": "-1", "note": "too long!"})

    assert response.status_code == 422
    assert {tuple(e["loc"]) for e in response.json()["errors"]} == {
        ("body", "amount"),
        ("body", "quantity"),
        ("body", "note"),
    }


def test_valid_input_still_works(client: TestClient) -> None:
    assert client.post("/things", json={"amount": "0", "quantity": "1", "note": "ok"}).status_code == 200
