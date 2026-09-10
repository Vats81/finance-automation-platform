import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.shared.infrastructure.ai_client import AnthropicAiClient, ConsoleAiClient, GroqAiClient


async def test_console_ai_client_returns_not_configured_fallback() -> None:
    client = ConsoleAiClient()

    response = await client.send(system="sys", messages=[], tools=[])

    assert response.stop_reason == "end_turn"
    assert response.tool_calls == []
    assert response.text is not None
    assert "GROQ_API_KEY" in response.text


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


def _mock_httpx_client(json_body: dict) -> tuple[MagicMock, MagicMock]:
    """Returns (async-context-manager mock, post mock). The post mock's
    call_args lets a test inspect the exact payload sent to Groq.
    """
    fake_response = MagicMock()
    fake_response.is_error = False
    fake_response.raise_for_status = MagicMock()
    fake_response.json = MagicMock(return_value=json_body)

    post = AsyncMock(return_value=fake_response)
    client = MagicMock()
    client.post = post
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client, post


def _groq_client() -> GroqAiClient:
    return GroqAiClient(api_key="test-key", model="llama-text", vision_model="llama-vision")


async def test_groq_ai_client_translates_text_only_response() -> None:
    client_mock, post = _mock_httpx_client(
        {"choices": [{"message": {"content": "Your revenue was $500."}, "finish_reason": "stop"}]}
    )

    with patch("app.shared.infrastructure.ai_client.httpx.AsyncClient", return_value=client_mock):
        response = await _groq_client().send(
            system="sys", messages=[{"role": "user", "content": "hi"}], tools=[]
        )

    assert response.text == "Your revenue was $500."
    assert response.tool_calls == []
    assert response.stop_reason == "end_turn"
    # system prompt is prepended as its own message
    sent = post.call_args.kwargs["json"]
    assert sent["messages"][0] == {"role": "system", "content": "sys"}
    assert sent["model"] == "llama-text"


async def test_groq_ai_client_translates_tool_call_response_and_maps_finish_reason() -> None:
    client_mock, _ = _mock_httpx_client(
        {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "get_business_summary",
                                    "arguments": json.dumps(
                                        {"start_date": "2026-01-01", "end_date": "2026-07-31"}
                                    ),
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }
    )

    with patch("app.shared.infrastructure.ai_client.httpx.AsyncClient", return_value=client_mock):
        response = await _groq_client().send(
            system="sys",
            messages=[{"role": "user", "content": "how are we doing?"}],
            tools=[
                {
                    "name": "get_business_summary",
                    "description": "totals for a range",
                    "input_schema": {"type": "object", "properties": {}},
                }
            ],
        )

    assert response.text is None
    assert response.stop_reason == "tool_use"
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].id == "call_1"
    assert response.tool_calls[0].name == "get_business_summary"
    assert response.tool_calls[0].input == {"start_date": "2026-01-01", "end_date": "2026-07-31"}


async def test_groq_ai_client_maps_anthropic_blocks_to_openai_shape() -> None:
    client_mock, post = _mock_httpx_client(
        {"choices": [{"message": {"content": "done"}, "finish_reason": "stop"}]}
    )
    # The tool-calling loop feeds back an assistant turn with a tool_use
    # block, then a user turn holding the tool_result — the exact shape
    # AskAssistantUseCase builds.
    messages = [
        {"role": "user", "content": "revenue?"},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "let me check"},
                {"type": "tool_use", "id": "call_1", "name": "get_business_summary", "input": {}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "call_1", "content": '{"total_revenue": "500"}'}
            ],
        },
    ]

    with patch("app.shared.infrastructure.ai_client.httpx.AsyncClient", return_value=client_mock):
        await _groq_client().send(system="sys", messages=messages, tools=[])

    sent_messages = post.call_args.kwargs["json"]["messages"]
    assert sent_messages[0]["role"] == "system"
    assert sent_messages[1] == {"role": "user", "content": "revenue?"}
    # assistant tool_use -> OpenAI tool_calls
    assert sent_messages[2]["role"] == "assistant"
    assert sent_messages[2]["tool_calls"][0]["id"] == "call_1"
    assert sent_messages[2]["tool_calls"][0]["function"]["name"] == "get_business_summary"
    # tool_result -> its own role:"tool" message, not nested in a user turn
    assert sent_messages[3] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": '{"total_revenue": "500"}',
    }


async def test_groq_ai_client_switches_to_vision_model_when_message_has_image() -> None:
    client_mock, post = _mock_httpx_client(
        {"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]}
    )
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": "abc123"},
                },
                {"type": "text", "text": "extract it"},
            ],
        }
    ]

    with patch("app.shared.infrastructure.ai_client.httpx.AsyncClient", return_value=client_mock):
        await _groq_client().send(system="sys", messages=messages, tools=[])

    sent = post.call_args.kwargs["json"]
    assert sent["model"] == "llama-vision"
    user_parts = sent["messages"][1]["content"]
    assert {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc123"}} in user_parts
    assert {"type": "text", "text": "extract it"} in user_parts
