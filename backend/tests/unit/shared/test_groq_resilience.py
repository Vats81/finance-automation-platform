import json

import httpx
import pytest

from app.shared.application.ports import AiProviderError
from app.shared.infrastructure import ai_client as ai_module
from app.shared.infrastructure.ai_client import GroqAiClient

_OK = {"choices": [{"message": {"content": "Done", "tool_calls": None}, "finish_reason": "stop"}]}
_TOOL_FAIL = {"error": {"code": "tool_use_failed", "message": "Failed to call a function"}}


def _client_with(monkeypatch: pytest.MonkeyPatch, responses: list[httpx.Response]) -> list[httpx.Request]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return responses[min(len(seen), len(responses)) - 1]

    real = httpx.AsyncClient
    monkeypatch.setattr(
        ai_module.httpx,
        "AsyncClient",
        lambda **kw: real(
            transport=httpx.MockTransport(handler), **{k: v for k, v in kw.items() if k != "transport"}
        ),
    )
    return seen


async def _send() -> object:
    return await GroqAiClient(api_key="k", model="m", vision_model="v").send(
        system="s", messages=[{"role": "user", "content": "hi"}], tools=[]
    )


async def test_a_tool_use_failed_400_is_retried_once_and_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _client_with(monkeypatch, [httpx.Response(400, json=_TOOL_FAIL), httpx.Response(200, json=_OK)])

    response = await _send()

    assert len(seen) == 2
    assert response.text == "Done"  # type: ignore[attr-defined]


async def test_other_provider_errors_become_a_clean_ai_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _client_with(monkeypatch, [httpx.Response(429, text=json.dumps({"error": "rate limited"}))])

    with pytest.raises(AiProviderError):
        await _send()

    assert len(seen) == 1  # not retried


async def test_a_persistent_tool_failure_gives_up_after_one_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _client_with(monkeypatch, [httpx.Response(400, json=_TOOL_FAIL)])

    with pytest.raises(AiProviderError):
        await _send()

    assert len(seen) == 2


async def test_a_network_failure_becomes_an_ai_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    real = httpx.AsyncClient
    monkeypatch.setattr(
        ai_module.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(boom))
    )

    with pytest.raises(AiProviderError):
        await _send()
