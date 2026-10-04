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
from app.inventory.application.commands.create_product import CreateProductCommand, CreateProductUseCase
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


async def test_prompt_says_score_unavailable_instead_of_none_for_a_new_business() -> None:
    # Regression test: a business with no history has overall_score=None,
    # and the prompt used to interpolate it as the literal "None/100" — the
    # model then repeated "score: None/100" back to the user.
    uow = FakeUnitOfWork()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Test Business")
    )
    ai_client = FakeAiClient([AiResponse(text="- ok", tool_calls=[], stop_reason="end_turn")])

    await GenerateInsightsUseCase(uow, ai_client, FakeClock(_NOW)).execute(
        GenerateInsightsCommand(business_id=business.id)
    )

    prompt = ai_client.calls[0]["messages"][0]["content"]
    assert "None" not in prompt
    assert "/100" not in prompt
    assert "not available yet" in prompt


async def test_prompt_says_inventory_untracked_when_there_are_no_products() -> None:
    # Regression test: with zero products the prompt only said "0 low-stock
    # products," which the model reported as "inventory is fully stocked."
    uow = FakeUnitOfWork()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Test Business")
    )
    ai_client = FakeAiClient([AiResponse(text="- ok", tool_calls=[], stop_reason="end_turn")])

    await GenerateInsightsUseCase(uow, ai_client, FakeClock(_NOW)).execute(
        GenerateInsightsCommand(business_id=business.id)
    )

    prompt = ai_client.calls[0]["messages"][0]["content"]
    assert "no products have been added yet" in prompt
    assert "low-stock or out-of-stock products: 0" not in prompt


async def test_prompt_reports_product_and_low_stock_counts_when_products_exist() -> None:
    uow = FakeUnitOfWork()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Test Business")
    )
    for sku, qty in (("OK-1", "100"), ("LOW-1", "1")):
        await CreateProductUseCase(uow).execute(
            CreateProductCommand(
                business_id=business.id,
                name=sku,
                sku=sku,
                selling_price=Decimal("10"),
                purchase_cost=Decimal("5"),
                current_quantity=Decimal(qty),
                minimum_stock_level=Decimal("10"),
            )
        )
    ai_client = FakeAiClient([AiResponse(text="- ok", tool_calls=[], stop_reason="end_turn")])

    await GenerateInsightsUseCase(uow, ai_client, FakeClock(_NOW)).execute(
        GenerateInsightsCommand(business_id=business.id)
    )

    prompt = ai_client.calls[0]["messages"][0]["content"]
    assert "Number of products tracked: 2" in prompt
    assert "low-stock or out-of-stock products: 1" in prompt
    assert "no products have been added yet" not in prompt


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
