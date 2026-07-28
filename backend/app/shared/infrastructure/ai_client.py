import anthropic

from app.shared.application.ports import AiResponse, AiToolCall, IAiClient

_NOT_CONFIGURED_MESSAGE = (
    "The AI Assistant isn't configured yet — add ANTHROPIC_API_KEY to enable real answers."
)


class ConsoleAiClient(IAiClient):
    """Dev fallback: returns a fixed "not configured" answer with no tool
    calls, so the assistant is testable end-to-end (request/response
    wiring, tool-loop termination) without a real Anthropic API key — same
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
