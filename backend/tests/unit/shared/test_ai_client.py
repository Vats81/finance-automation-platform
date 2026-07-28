from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.shared.infrastructure.ai_client import AnthropicAiClient, ConsoleAiClient


async def test_console_ai_client_returns_not_configured_fallback() -> None:
    client = ConsoleAiClient()

    response = await client.send(system="sys", messages=[], tools=[])

    assert response.stop_reason == "end_turn"
    assert response.tool_calls == []
    assert response.text is not None
    assert "ANTHROPIC_API_KEY" in response.text


def _mock_anthropic_client(fake_response: SimpleNamespace) -> MagicMock:
    mock_messages = MagicMock()
    mock_messages.create = AsyncMock(return_value=fake_response)
    mock_client = MagicMock()
    mock_client.messages = mock_messages
    return mock_client


async def test_anthropic_ai_client_translates_text_only_response() -> None:
    fake_response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="Your revenue was $500.")],
        stop_reason="end_turn",
    )

    with patch(
        "app.shared.infrastructure.ai_client.anthropic.AsyncAnthropic",
        return_value=_mock_anthropic_client(fake_response),
    ):
        client = AnthropicAiClient(api_key="test-key", model="claude-sonnet-5")
        response = await client.send(
            system="sys", messages=[{"role": "user", "content": "hi"}], tools=[]
        )

    assert response.text == "Your revenue was $500."
    assert response.tool_calls == []
    assert response.stop_reason == "end_turn"


async def test_anthropic_ai_client_translates_tool_use_response() -> None:
    fake_response = SimpleNamespace(
        content=[
            SimpleNamespace(
                type="tool_use",
                id="tool_1",
                name="get_business_summary",
                input={"start_date": "2026-01-01", "end_date": "2026-07-31"},
            )
        ],
        stop_reason="tool_use",
    )

    with patch(
        "app.shared.infrastructure.ai_client.anthropic.AsyncAnthropic",
        return_value=_mock_anthropic_client(fake_response),
    ):
        client = AnthropicAiClient(api_key="test-key", model="claude-sonnet-5")
        response = await client.send(system="sys", messages=[], tools=[])

    assert response.text is None
    assert response.stop_reason == "tool_use"
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "get_business_summary"
    assert response.tool_calls[0].input == {"start_date": "2026-01-01", "end_date": "2026-07-31"}
