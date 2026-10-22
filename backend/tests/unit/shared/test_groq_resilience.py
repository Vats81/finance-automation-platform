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
    seen = _client_with(monkeypatch, [httpx.Response(401, text=json.dumps({"error": "bad key"}))])

    with pytest.raises(AiProviderError):
        await _send()

    assert len(seen) == 1  # a non-transient error is not retried


async def test_a_persistent_tool_failure_gives_up_after_three_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_sleep(_: float) -> None: ...

    monkeypatch.setattr(ai_module.asyncio, "sleep", no_sleep)
    seen = _client_with(monkeypatch, [httpx.Response(400, json=_TOOL_FAIL)])

    with pytest.raises(AiProviderError):
        await _send()

    assert len(seen) == 3


async def test_a_network_failure_becomes_an_ai_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_sleep(_: float) -> None: ...

    monkeypatch.setattr(ai_module.asyncio, "sleep", no_sleep)

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    real = httpx.AsyncClient
    monkeypatch.setattr(
        ai_module.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(boom))
    )

    with pytest.raises(AiProviderError):
        await _send()


@pytest.mark.parametrize("status", [429, 500, 502, 503])
async def test_transient_provider_errors_are_retried_then_succeed(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    async def no_sleep(_: float) -> None: ...

    monkeypatch.setattr(ai_module.asyncio, "sleep", no_sleep)
    seen = _client_with(
        monkeypatch,
        [
            httpx.Response(status, text="busy"),
            httpx.Response(status, text="busy"),
            httpx.Response(200, json=_OK),
        ],
    )

    response = await _send()

    assert len(seen) == 3
    assert response.text == "Done"  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "bad_body",
    [
        {"choices": []},
        {},
        {"choices": [{"message": {"content": None, "tool_calls": None}}]},
        {"choices": [None]},
    ],
)
async def test_an_empty_or_malformed_200_is_retried_and_never_a_crash(
    monkeypatch: pytest.MonkeyPatch, bad_body: dict
) -> None:
    async def no_sleep(_: float) -> None: ...

    monkeypatch.setattr(ai_module.asyncio, "sleep", no_sleep)
    seen = _client_with(monkeypatch, [httpx.Response(200, json=bad_body)])

    with pytest.raises(AiProviderError):
        await _send()

    assert len(seen) == 3


async def test_a_flaky_empty_answer_then_a_good_one_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_sleep(_: float) -> None: ...

    monkeypatch.setattr(ai_module.asyncio, "sleep", no_sleep)
    _client_with(monkeypatch, [httpx.Response(200, json={"choices": []}), httpx.Response(200, json=_OK)])

    assert (await _send()).text == "Done"  # type: ignore[attr-defined]


async def test_a_rate_limit_waits_as_long_as_the_provider_asks_up_to_a_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    waits: list[float] = []

    async def record(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr(ai_module.asyncio, "sleep", record)
    _client_with(
        monkeypatch,
        [
            httpx.Response(429, headers={"retry-after": "3"}, text="slow down"),
            httpx.Response(429, headers={"retry-after": "120"}, text="slow down"),
            httpx.Response(200, json=_OK),
        ],
    )

    assert (await _send()).text == "Done"  # type: ignore[attr-defined]
    assert waits == [3.0, 8.0]  # the second hint is capped so a request can't hang


async def test_the_provider_status_and_code_travel_with_the_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_sleep(_: float) -> None: ...

    monkeypatch.setattr(ai_module.asyncio, "sleep", no_sleep)
    _client_with(
        monkeypatch, [httpx.Response(429, json={"error": {"code": "rate_limit_exceeded", "message": "x"}})]
    )

    with pytest.raises(AiProviderError) as caught:
        await _send()

    assert caught.value.status_code == 429 and caught.value.code == "rate_limit_exceeded"
