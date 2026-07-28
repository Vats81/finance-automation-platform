import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from app.ai_assistant.application.generate_insights import (
    GenerateInsightsCommand,
    GenerateInsightsUseCase,
)
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
from app.shared.application.ports import AiResponse
from tests.fakes.fake_ports import FakeAiClient, FakeClock
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

_NOW = datetime(2026, 7, 24, tzinfo=timezone.utc)


async def test_prompt_embeds_real_figures_and_returns_ai_text() -> None:
    uow = FakeUnitOfWork()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Test Business")
    )
    await CreateSaleUseCase(uow).execute(
        CreateSaleCommand(
            business_id=business.id,
            invoice_number="INV-1",
            invoice_date=date(2026, 7, 10),
            line_items=[
                CreateSaleLineItemInput(
                    line_number=1, description="Item", quantity=Decimal("1"), unit_price=Decimal("500")
                )
            ],
        )
    )
    ai_client = FakeAiClient(
        [
            AiResponse(
                text="- Revenue is strong\n- Follow up on unpaid invoices",
                tool_calls=[],
                stop_reason="end_turn",
            )
        ]
    )

    result = await GenerateInsightsUseCase(uow, ai_client, FakeClock(_NOW)).execute(
        GenerateInsightsCommand(business_id=business.id)
    )

    assert result.insights == "- Revenue is strong\n- Follow up on unpaid invoices"
    assert len(ai_client.calls) == 1
    prompt = ai_client.calls[0]["messages"][0]["content"]
    assert "500.00" in prompt
    assert "Business Health Score" in prompt


async def test_falls_back_when_ai_returns_no_text() -> None:
    uow = FakeUnitOfWork()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Test Business")
    )
    ai_client = FakeAiClient([AiResponse(text=None, tool_calls=[], stop_reason="end_turn")])

    result = await GenerateInsightsUseCase(uow, ai_client, FakeClock(_NOW)).execute(
        GenerateInsightsCommand(business_id=business.id)
    )

    assert result.insights == "Not enough data to generate insights yet."
