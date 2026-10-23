"""A business's currency is dollars or rupees; it changes how amounts are written, never the amounts."""

import uuid
from decimal import Decimal

import pytest

from app.ai_assistant.application.ask_assistant import AskAssistantCommand, AskAssistantUseCase
from app.business.application.commands.complete_onboarding import (
    CompleteOnboardingCommand,
    CompleteOnboardingUseCase,
)
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.dashboard.application.pdf_generator import _format_currency
from app.shared.application.ports import AiResponse
from app.shared.domain.exceptions import ValidationException
from tests.fakes.fake_ports import FakeAiClient
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


async def _business(uow: FakeUnitOfWork, currency: str | None = None) -> uuid.UUID:
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Acme")
    )
    if currency:
        await CompleteOnboardingUseCase(uow).execute(
            CompleteOnboardingCommand(business_id=business.id, currency=currency)
        )
    return business.id


async def test_a_new_business_uses_dollars() -> None:
    uow = FakeUnitOfWork()
    business_id = await _business(uow)

    assert (await uow.businesses.get_by_id(business_id)).currency == "USD"  # type: ignore[union-attr]


@pytest.mark.parametrize("currency", ["USD", "INR"])
async def test_dollars_and_rupees_can_be_chosen(currency: str) -> None:
    uow = FakeUnitOfWork()
    business_id = await _business(uow, currency)

    assert (await uow.businesses.get_by_id(business_id)).currency == currency  # type: ignore[union-attr]


@pytest.mark.parametrize("currency", ["EUR", "usd", "", "RS"])
async def test_other_currencies_are_refused(currency: str) -> None:
    uow = FakeUnitOfWork()
    business_id = await _business(uow)

    with pytest.raises(ValidationException):
        await CompleteOnboardingUseCase(uow).execute(
            CompleteOnboardingCommand(business_id=business_id, currency=currency)
        )


@pytest.mark.parametrize(
    ("amount", "currency", "expected"),
    [
        ("1234.5", "USD", "$1,234.50"),
        ("-5", "USD", "-$5.00"),
        ("1234567.891", "INR", "Rs. 12,34,567.89"),
        ("999", "INR", "Rs. 999.00"),
        ("1000", "INR", "Rs. 1,000.00"),
        ("100000", "INR", "Rs. 1,00,000.00"),
        ("-50.5", "INR", "-Rs. 50.50"),
        ("0", "INR", "Rs. 0.00"),
    ],
)
def test_pdf_amounts_are_written_in_the_business_currency(amount: str, currency: str, expected: str) -> None:
    assert _format_currency(Decimal(amount), currency) == expected


async def test_the_assistant_is_told_which_currency_to_use() -> None:
    uow = FakeUnitOfWork()
    rupees, dollars = await _business(uow, "INR"), await _business(uow)

    for business_id, expected in ((rupees, "rupee"), (dollars, "US dollars")):
        ai_client = FakeAiClient([AiResponse(text="ok", tool_calls=[], stop_reason="end_turn")])
        await AskAssistantUseCase(uow, ai_client).execute(
            AskAssistantCommand(business_id=business_id, question="Hello")
        )
        assert expected in ai_client.calls[0]["system"]


def test_rupees_use_the_rupee_sign_except_where_the_font_cannot() -> None:
    from app.shared.domain.money_format import format_money

    assert format_money(Decimal("1234567.5"), "INR") == "₹12,34,567.50"
    assert format_money(Decimal("1234567.5"), "INR", plain=True) == "Rs. 12,34,567.50"
    assert format_money(Decimal("1234567.5"), "USD") == "$1,234,567.50"
