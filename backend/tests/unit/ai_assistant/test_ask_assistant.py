import uuid
from datetime import date
from decimal import Decimal

from app.ai_assistant.application.ask_assistant import AskAssistantCommand, AskAssistantUseCase
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
from app.shared.application.ports import AiResponse, AiToolCall
from tests.fakes.fake_ports import FakeAiClient
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


async def test_answers_directly_with_no_tool_calls() -> None:
    uow = FakeUnitOfWork()
    ai_client = FakeAiClient(
        [AiResponse(text="Hi, how can I help?", tool_calls=[], stop_reason="end_turn")]
    )

    result = await AskAssistantUseCase(uow, ai_client).execute(
        AskAssistantCommand(business_id=uuid.uuid4(), question="Hello")
    )

    assert result.answer == "Hi, how can I help?"
    assert len(ai_client.calls) == 1
    assert result.history[-1] == {"role": "assistant", "content": "Hi, how can I help?"}


async def test_executes_a_requested_tool_then_answers() -> None:
    uow = FakeUnitOfWork()
    owner_id = uuid.uuid4()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=owner_id, name="Jane's Diner Supplies")
    )
    await CreateSaleUseCase(uow).execute(
        CreateSaleCommand(
            business_id=business.id,
            invoice_number="INV-1",
            invoice_date=date(2026, 7, 20),
            line_items=[
                CreateSaleLineItemInput(
                    line_number=1, description="Widget", quantity=Decimal("1"), unit_price=Decimal("500")
                )
            ],
        )
    )

    ai_client = FakeAiClient(
        [
            AiResponse(
                text=None,
                tool_calls=[
                    AiToolCall(
                        id="tool_1",
                        name="get_business_summary",
                        input={"start_date": "2026-07-01", "end_date": "2026-07-31"},
                    )
                ],
                stop_reason="tool_use",
            ),
            AiResponse(text="Your revenue was $500.00.", tool_calls=[], stop_reason="end_turn"),
        ]
    )

    result = await AskAssistantUseCase(uow, ai_client).execute(
        AskAssistantCommand(business_id=business.id, question="What was my revenue in July?")
    )

    assert result.answer == "Your revenue was $500.00."
    assert len(ai_client.calls) == 2
    # The second call should include the tool_result with the real total.
    second_call_messages = ai_client.calls[1]["messages"]
    tool_result_message = next(
        m for m in second_call_messages if m["role"] == "user" and isinstance(m["content"], list)
    )
    assert "500.00" in tool_result_message["content"][0]["content"]


async def test_undeclared_tool_arguments_are_ignored_instead_of_erroring() -> None:
    # Regression test, seen live against Groq: the model called
    # list_low_stock_products (which declares no parameters) with an
    # invented `limit`, the strict handler raised a TypeError, and a round
    # trip was spent on "Error running list_low_stock_products...".
    uow = FakeUnitOfWork()
    ai_client = FakeAiClient(
        [
            AiResponse(
                text=None,
                tool_calls=[AiToolCall(id="tool_1", name="list_low_stock_products", input={"limit": 5})],
                stop_reason="tool_use",
            ),
            AiResponse(text="You have no products yet.", tool_calls=[], stop_reason="end_turn"),
        ]
    )

    result = await AskAssistantUseCase(uow, ai_client).execute(
        AskAssistantCommand(business_id=uuid.uuid4(), question="Is anything low on stock?")
    )

    assert result.answer == "You have no products yet."
    tool_result = next(
        m for m in ai_client.calls[1]["messages"] if m["role"] == "user" and isinstance(m["content"], list)
    )["content"][0]["content"]
    assert not tool_result.startswith("Error")
    assert '"total_products": 0' in tool_result


async def test_declared_tool_arguments_are_still_passed_through() -> None:
    uow = FakeUnitOfWork()
    ai_client = FakeAiClient(
        [
            AiResponse(
                text=None,
                tool_calls=[
                    AiToolCall(
                        id="tool_1",
                        name="get_business_summary",
                        input={"start_date": "2026-07-01", "end_date": "2026-07-31", "currency": "EUR"},
                    )
                ],
                stop_reason="tool_use",
            ),
            AiResponse(text="Done.", tool_calls=[], stop_reason="end_turn"),
        ]
    )

    await AskAssistantUseCase(uow, ai_client).execute(
        AskAssistantCommand(business_id=uuid.uuid4(), question="July summary")
    )

    tool_result = next(
        m for m in ai_client.calls[1]["messages"] if m["role"] == "user" and isinstance(m["content"], list)
    )["content"][0]["content"]
    # Required, declared args reached the handler (so it produced real
    # totals) while the undeclared `currency` was dropped without an error.
    assert "total_revenue" in tool_result
    assert not tool_result.startswith("Error")


async def test_stops_at_the_round_trip_cap() -> None:
    uow = FakeUnitOfWork()
    always_tool_use = AiResponse(
        text=None,
        tool_calls=[AiToolCall(id="tool_x", name="list_customers", input={})],
        stop_reason="tool_use",
    )
    ai_client = FakeAiClient([always_tool_use] * 5)

    result = await AskAssistantUseCase(uow, ai_client).execute(
        AskAssistantCommand(business_id=uuid.uuid4(), question="Loop forever")
    )

    assert len(ai_client.calls) == 5
    assert "wasn't able" in result.answer.lower() or "rephrasing" in result.answer.lower()


async def test_unknown_tool_name_reports_error_without_crashing() -> None:
    uow = FakeUnitOfWork()
    ai_client = FakeAiClient(
        [
            AiResponse(
                text=None,
                tool_calls=[AiToolCall(id="tool_1", name="not_a_real_tool", input={})],
                stop_reason="tool_use",
            ),
            AiResponse(text="I couldn't find that information.", tool_calls=[], stop_reason="end_turn"),
        ]
    )

    result = await AskAssistantUseCase(uow, ai_client).execute(
        AskAssistantCommand(business_id=uuid.uuid4(), question="Do something unsupported")
    )

    assert result.answer == "I couldn't find that information."
