import base64
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from app.expenses.domain.exceptions import (
    ReceiptFileTooLargeException,
    UnsupportedReceiptFileTypeException,
)
from app.shared.application.ports import IAiClient

# Claude vision's realistically-relevant receipt formats.
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Anthropic caps images at 5MB base64-encoded; base64 inflates raw bytes by
# ~4/3, so this raw-upload cap is set conservatively below that to leave
# headroom rather than relying on an exact boundary.
_MAX_FILE_SIZE_BYTES = 3 * 1024 * 1024

_SYSTEM_PROMPT = (
    "You are a receipt-scanning assistant for a small business expense tracker. Given a photo of a "
    "receipt, extract: vendor_name (string or null), amount (the total amount as a plain number, or "
    "null), expense_date (the receipt's date as YYYY-MM-DD, or null), category_guess (a short category "
    "like Rent, Utilities, Supplies, Travel, Meals, Marketing, or Other, or null), and description_guess "
    "(a short one-line description of the purchase, or null). Respond with ONLY a JSON object with "
    "exactly these five keys — no other text, no markdown formatting."
)


@dataclass(frozen=True)
class ScanReceiptCommand:
    content_type: str
    image_bytes: bytes


@dataclass(frozen=True)
class ScannedReceiptData:
    vendor_name: str | None
    amount: Decimal | None
    expense_date: date | None
    category_guess: str | None
    description_guess: str | None
    raw_text: str


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def _parse_amount(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


class ScanReceiptUseCase:
    """Extracts structured fields from a receipt photo by sending it to
    Claude as an image content block — no new AI provider or OCR library:
    IAiClient.send() already forwards raw message dicts untouched, and
    Anthropic's Messages API already supports image content blocks in that
    same shape. Single-shot (tools=[]), same pattern as
    GenerateInsightsUseCase, since there's nothing for the model to decide
    to fetch.

    Never raises on a malformed/non-JSON AI response (including
    ConsoleAiClient's fixed, non-JSON fallback sentence when no API key is
    configured) — a bad or absent AI response degrades to all-None fields
    plus the raw response text, never a crash, since the caller only ever
    uses this to pre-fill a form the user reviews before submitting.
    """

    def __init__(self, ai_client: IAiClient) -> None:
        self._ai_client = ai_client

    async def execute(self, command: ScanReceiptCommand) -> ScannedReceiptData:
        if command.content_type not in _ALLOWED_CONTENT_TYPES:
            raise UnsupportedReceiptFileTypeException(
                f"Unsupported file type: {command.content_type or 'unknown'}"
            )
        if len(command.image_bytes) > _MAX_FILE_SIZE_BYTES:
            raise ReceiptFileTooLargeException(
                f"File exceeds the {_MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB limit"
            )

        image_data = base64.b64encode(command.image_bytes).decode()
        response = await self._ai_client.send(
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": command.content_type,
                                "data": image_data,
                            },
                        },
                        {"type": "text", "text": "Extract the receipt details as instructed."},
                    ],
                }
            ],
            tools=[],
        )

        raw_text = response.text or ""
        try:
            parsed = json.loads(_strip_json_fence(raw_text))
        except json.JSONDecodeError:
            return ScannedReceiptData(
                vendor_name=None,
                amount=None,
                expense_date=None,
                category_guess=None,
                description_guess=None,
                raw_text=raw_text,
            )

        return ScannedReceiptData(
            vendor_name=_parse_str(parsed.get("vendor_name")),
            amount=_parse_amount(parsed.get("amount")),
            expense_date=_parse_date(parsed.get("expense_date")),
            category_guess=_parse_str(parsed.get("category_guess")),
            description_guess=_parse_str(parsed.get("description_guess")),
            raw_text=raw_text,
        )
