import json
import uuid
from dataclasses import dataclass

from app.ai_assistant.application.tools import TOOL_HANDLERS, TOOL_SCHEMAS
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.shared.application.ports import IAiClient

_SYSTEM_PROMPT = (
    "You are FinanceAI's business assistant. Answer questions about the user's business using the "
    "provided tools to fetch real data — never guess or make up numbers. Keep answers concise and "
    "format currency amounts clearly."
)

_MAX_TOOL_ROUND_TRIPS = 5
_FALLBACK_MESSAGE = "I wasn't able to finish answering that — could you try rephrasing your question?"


@dataclass(frozen=True)
class AskAssistantCommand:
    business_id: uuid.UUID
    question: str
    history: list[dict] | None = None


@dataclass(frozen=True)
class AskAssistantResult:
    answer: str
    history: list[dict]


class AskAssistantUseCase:
    """Runs the tool-calling loop: Claude decides which read-only tools
    (tools.py — each a thin wrapper around an existing query use case) it
    needs to answer, we execute them, and feed the results back until
    Claude produces a final text answer. Capped at _MAX_TOOL_ROUND_TRIPS to
    prevent a runaway loop; conversation is stateless — the caller passes
    the prior history back in and gets the updated history back out.
    """

    def __init__(self, uow: AppUnitOfWork, ai_client: IAiClient) -> None:
        self._uow = uow
        self._ai_client = ai_client

    async def execute(self, command: AskAssistantCommand) -> AskAssistantResult:
        messages = list(command.history or [])
        messages.append({"role": "user", "content": command.question})

        for _ in range(_MAX_TOOL_ROUND_TRIPS):
            response = await self._ai_client.send(
                system=_SYSTEM_PROMPT, messages=messages, tools=TOOL_SCHEMAS
            )

            if response.stop_reason != "tool_use" or not response.tool_calls:
                answer = response.text or _FALLBACK_MESSAGE
                messages.append({"role": "assistant", "content": answer})
                return AskAssistantResult(answer=answer, history=messages)

            assistant_content: list[dict] = []
            if response.text:
                assistant_content.append({"type": "text", "text": response.text})
            for tool_call in response.tool_calls:
                assistant_content.append(
                    {"type": "tool_use", "id": tool_call.id, "name": tool_call.name, "input": tool_call.input}
                )
            messages.append({"role": "assistant", "content": assistant_content})

            tool_results = []
            for tool_call in response.tool_calls:
                handler = TOOL_HANDLERS.get(tool_call.name)
                if handler is None:
                    result_content = f"Unknown tool: {tool_call.name}"
                else:
                    try:
                        result = await handler(self._uow, command.business_id, **tool_call.input)
                        result_content = json.dumps(result)
                    except Exception as exc:  # noqa: BLE001 - a bad tool call must not crash the request
                        result_content = f"Error running {tool_call.name}: {exc}"
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": tool_call.id, "content": result_content}
                )
            messages.append({"role": "user", "content": tool_results})

        return AskAssistantResult(answer=_FALLBACK_MESSAGE, history=messages)
