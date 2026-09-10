import json
import logging
from typing import Any

import anthropic
import httpx

from app.shared.application.ports import AiResponse, AiToolCall, IAiClient

logger = logging.getLogger(__name__)

_NOT_CONFIGURED_MESSAGE = (
    "The AI Assistant isn't configured yet — add GROQ_API_KEY (free) or ANTHROPIC_API_KEY to enable "
    "real answers."
)

_GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


class ConsoleAiClient(IAiClient):
    """Dev fallback: returns a fixed "not configured" answer with no tool
    calls, so the assistant is testable end-to-end (request/response
    wiring, tool-loop termination) without a real API key — same
    swap-by-settings idea as ConsoleEmailSender/ConsoleWhatsAppSender.
    """

    async def send(self, *, system: str, messages: list[dict], tools: list[dict]) -> AiResponse:
        return AiResponse(text=_NOT_CONFIGURED_MESSAGE, tool_calls=[], stop_reason="end_turn")


class AnthropicAiClient(IAiClient):
    def __init__(self, *, api_key: str, model: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def send(self, *, system: str, messages: list[dict], tools: list[dict]) -> AiResponse:
        # IAiClient deliberately keeps messages/tools as plain dicts (see the
        # port's docstring) rather than importing anthropic's TypedDicts
        # into the port — the SDK's own types are narrower than `dict`, so
        # this is a real, expected mismatch, not a bug.
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=messages,  # type: ignore[arg-type]
            tools=tools,  # type: ignore[arg-type]
        )

        text_parts = [block.text for block in response.content if block.type == "text"]
        tool_calls = [
            AiToolCall(id=block.id, name=block.name, input=block.input)
            for block in response.content
            if block.type == "tool_use"
        ]

        return AiResponse(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason or "end_turn",
        )


class GroqAiClient(IAiClient):
    """Free-tier alternative to AnthropicAiClient, talking to Groq's
    OpenAI-compatible chat-completions endpoint over plain httpx (no SDK,
    same as TwilioWhatsAppSender / ResendApiEmailSender).

    Everything upstream of IAiClient speaks the Anthropic Messages API
    JSON shape — role/content messages, `text`/`image`/`tool_use`/
    `tool_result` content blocks, `input_schema` tool defs (see the port's
    docstring). This adapter translates that shape into OpenAI's chat
    format on the way out and back on the way in, so AskAssistantUseCase /
    GenerateInsightsUseCase / ScanReceiptUseCase need no changes.

    When any message carries an image block (the Receipt Scanner), it
    switches to `vision_model` for that call — the default text model
    can't see images.
    """

    def __init__(self, *, api_key: str, model: str, vision_model: str) -> None:
        self._api_key = api_key
        self._model = model
        self._vision_model = vision_model

    async def send(self, *, system: str, messages: list[dict], tools: list[dict]) -> AiResponse:
        oai_messages: list[dict] = [{"role": "system", "content": system}]
        has_image = False
        for message in messages:
            translated, saw_image = _to_openai_messages(message)
            oai_messages.extend(translated)
            has_image = has_image or saw_image

        payload: dict[str, Any] = {
            "model": self._vision_model if has_image else self._model,
            "messages": oai_messages,
            "max_tokens": 1024,
        }
        if tools:
            payload["tools"] = [_to_openai_tool(tool) for tool in tools]

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                _GROQ_CHAT_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )
            if response.is_error:
                # Groq's JSON error body (code/message) is far more useful
                # than httpx's generic "400 Bad Request" — log it before
                # raising so it shows up in production logs.
                logger.error("Groq request failed (%s): %s", response.status_code, response.text)
            response.raise_for_status()
            data = response.json()

        choice = data["choices"][0]
        oai_message = choice["message"]

        tool_calls = [
            AiToolCall(
                id=call["id"],
                name=call["function"]["name"],
                input=_loads_dict_or_empty(call["function"].get("arguments")),
            )
            for call in (oai_message.get("tool_calls") or [])
        ]
        stop_reason = "tool_use" if choice.get("finish_reason") == "tool_calls" else "end_turn"
        return AiResponse(
            text=oai_message.get("content") or None,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
        )


def _loads_dict_or_empty(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _to_openai_tool(tool: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema") or {"type": "object", "properties": {}},
        },
    }


def _to_openai_messages(message: dict) -> tuple[list[dict], bool]:
    """Translate one Anthropic-shape message into one or more OpenAI-shape
    messages. A user turn whose content list holds `tool_result` blocks
    becomes one `role: "tool"` message per result (OpenAI carries tool
    output in its own role, not nested inside a user turn). Returns
    (messages, whether any image block was present).
    """
    role = message["role"]
    content = message["content"]

    if isinstance(content, str):
        return [{"role": role, "content": content}], False

    tool_result_messages: list[dict] = []
    text_parts: list[str] = []
    content_parts: list[dict] = []
    tool_calls: list[dict] = []
    has_image = False

    for block in content:
        block_type = block.get("type")
        if block_type == "text":
            text_parts.append(block["text"])
            content_parts.append({"type": "text", "text": block["text"]})
        elif block_type == "image":
            has_image = True
            source = block["source"]
            content_parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{source['media_type']};base64,{source['data']}"},
                }
            )
        elif block_type == "tool_use":
            tool_calls.append(
                {
                    "id": block["id"],
                    "type": "function",
                    "function": {
                        "name": block["name"],
                        "arguments": json.dumps(block.get("input", {})),
                    },
                }
            )
        elif block_type == "tool_result":
            tool_result_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": block["tool_use_id"],
                    "content": block.get("content", ""),
                }
            )

    if tool_result_messages:
        return tool_result_messages, has_image

    if role == "assistant":
        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": "\n".join(text_parts) or None,
        }
        if tool_calls:
            assistant_message["tool_calls"] = tool_calls
        return [assistant_message], has_image

    # A user turn: send structured parts when there's an image to carry,
    # otherwise flatten to plain text.
    if has_image:
        return [{"role": "user", "content": content_parts}], has_image
    return [{"role": "user", "content": "\n".join(text_parts)}], has_image
