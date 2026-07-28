import json
from datetime import date
from decimal import Decimal

import pytest

from app.expenses.application.scan_receipt import ScanReceiptCommand, ScanReceiptUseCase
from app.expenses.domain.exceptions import (
    ReceiptFileTooLargeException,
    UnsupportedReceiptFileTypeException,
)
from app.shared.application.ports import AiResponse
from tests.fakes.fake_ports import FakeAiClient

_VALID_JSON = json.dumps(
    {
        "vendor_name": "Acme Supplies",
        "amount": 42.50,
        "expense_date": "2026-07-15",
        "category_guess": "Supplies",
        "description_guess": "Office supplies purchase",
    }
)


async def test_valid_json_response_is_parsed_and_image_block_is_sent() -> None:
    ai_client = FakeAiClient([AiResponse(text=_VALID_JSON, tool_calls=[], stop_reason="end_turn")])

    result = await ScanReceiptUseCase(ai_client).execute(
        ScanReceiptCommand(content_type="image/jpeg", image_bytes=b"fake-image-bytes")
    )

    assert result.vendor_name == "Acme Supplies"
    assert result.amount == Decimal("42.5")
    assert result.expense_date == date(2026, 7, 15)
    assert result.category_guess == "Supplies"
    assert result.description_guess == "Office supplies purchase"

    assert len(ai_client.calls) == 1
    content_blocks = ai_client.calls[0]["messages"][0]["content"]
    image_block = next(b for b in content_blocks if b["type"] == "image")
    assert image_block["source"]["media_type"] == "image/jpeg"
    assert image_block["source"]["type"] == "base64"


async def test_console_fallback_non_json_response_degrades_gracefully() -> None:
    fallback_text = "The AI Assistant isn't configured yet — add ANTHROPIC_API_KEY to enable real answers."
    ai_client = FakeAiClient([AiResponse(text=fallback_text, tool_calls=[], stop_reason="end_turn")])

    result = await ScanReceiptUseCase(ai_client).execute(
        ScanReceiptCommand(content_type="image/png", image_bytes=b"fake-image-bytes")
    )

    assert result.vendor_name is None
    assert result.amount is None
    assert result.expense_date is None
    assert result.category_guess is None
    assert result.description_guess is None
    assert result.raw_text == fallback_text


async def test_markdown_fenced_json_is_stripped_and_parsed() -> None:
    fenced = f"```json\n{_VALID_JSON}\n```"
    ai_client = FakeAiClient([AiResponse(text=fenced, tool_calls=[], stop_reason="end_turn")])

    result = await ScanReceiptUseCase(ai_client).execute(
        ScanReceiptCommand(content_type="image/jpeg", image_bytes=b"fake-image-bytes")
    )

    assert result.vendor_name == "Acme Supplies"
    assert result.amount == Decimal("42.5")


async def test_partial_json_leaves_missing_keys_as_none() -> None:
    partial = json.dumps({"vendor_name": "Acme Supplies", "amount": 10})
    ai_client = FakeAiClient([AiResponse(text=partial, tool_calls=[], stop_reason="end_turn")])

    result = await ScanReceiptUseCase(ai_client).execute(
        ScanReceiptCommand(content_type="image/jpeg", image_bytes=b"fake-image-bytes")
    )

    assert result.vendor_name == "Acme Supplies"
    assert result.amount == Decimal("10")
    assert result.expense_date is None
    assert result.category_guess is None
    assert result.description_guess is None


async def test_invalid_field_values_become_none_without_crashing() -> None:
    bad_values = json.dumps(
        {
            "vendor_name": "Acme Supplies",
            "amount": "not a number",
            "expense_date": "not a date",
            "category_guess": "Supplies",
            "description_guess": None,
        }
    )
    ai_client = FakeAiClient([AiResponse(text=bad_values, tool_calls=[], stop_reason="end_turn")])

    result = await ScanReceiptUseCase(ai_client).execute(
        ScanReceiptCommand(content_type="image/jpeg", image_bytes=b"fake-image-bytes")
    )

    assert result.vendor_name == "Acme Supplies"
    assert result.amount is None
    assert result.expense_date is None
    assert result.category_guess == "Supplies"
    assert result.description_guess is None


async def test_unsupported_content_type_raises() -> None:
    ai_client = FakeAiClient([])

    with pytest.raises(UnsupportedReceiptFileTypeException):
        await ScanReceiptUseCase(ai_client).execute(
            ScanReceiptCommand(content_type="application/pdf", image_bytes=b"fake-bytes")
        )


async def test_oversized_file_raises() -> None:
    ai_client = FakeAiClient([])
    oversized = b"x" * (3 * 1024 * 1024 + 1)

    with pytest.raises(ReceiptFileTooLargeException):
        await ScanReceiptUseCase(ai_client).execute(
            ScanReceiptCommand(content_type="image/jpeg", image_bytes=oversized)
        )
