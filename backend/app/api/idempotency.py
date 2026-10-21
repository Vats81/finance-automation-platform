"""Idempotency-Key support for business-scoped POSTs.

A double-click, a retry after a timeout, or a flaky mobile connection used to
create the same sale/expense twice (five concurrent identical POSTs stored five
rows). A client now sends a unique `Idempotency-Key` per form submission and
reuses it on every retry of that submission:

* first request with a key: runs normally; a 2xx response is stored;
* a repeat (same key, same request): the stored response is replayed
  (`Idempotent-Replay: true`) and nothing is created again;
* a repeat while the first is still running: 409, try again shortly;
* the same key with a different request body: 422 (a client bug).

Failed (non-2xx) responses are not stored, so correcting the input and
retrying with the same key works. Requests without the header behave as before.
Keys are scoped to the caller's bearer token + method + path, so one user's key
can never collide with, or replay for, another's.
"""

import hashlib
import json
import logging
import re
from collections.abc import Awaitable, Callable, MutableMapping
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy import delete, extract, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.audit.infrastructure.models import IdempotencyKeyModel
from app.bootstrap.container import get_container

logger = logging.getLogger(__name__)

Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]

HEADER = b"idempotency-key"
_PATH = re.compile(r"^/api/v1/businesses/[0-9a-fA-F-]{36}/")
_MAX_KEY_LENGTH = 100
_MAX_BODY_BYTES = 1024 * 1024
_MAX_STORED_RESPONSE_BYTES = 64 * 1024
_PENDING_STALE_SECONDS = 60
_KEEP_HOURS = 24


@dataclass(frozen=True)
class Stored:
    status_code: int
    body: bytes
    content_type: str


@dataclass(frozen=True)
class Claim:
    outcome: str  # "new" | "replay" | "in_progress" | "mismatch"
    stored: Stored | None = None


class IdempotencyStore(Protocol):
    async def claim(self, key_hash: str, request_hash: str) -> Claim: ...

    async def complete(self, key_hash: str, stored: Stored) -> None: ...

    async def release(self, key_hash: str) -> None: ...


class DatabaseIdempotencyStore:
    async def claim(self, key_hash: str, request_hash: str) -> Claim:
        async with get_container().session_factory() as session:
            await session.execute(
                delete(IdempotencyKeyModel).where(
                    IdempotencyKeyModel.created_at < func.now() - func.make_interval(0, 0, 0, 0, _KEEP_HOURS)
                )
            )
            inserted = await session.execute(
                pg_insert(IdempotencyKeyModel)
                .values(key_hash=key_hash, request_hash=request_hash, state="pending")
                .on_conflict_do_nothing(index_elements=["key_hash"])
                .returning(IdempotencyKeyModel.key_hash)
            )
            if inserted.first() is not None:
                await session.commit()
                return Claim("new")

            row = (
                await session.execute(
                    select(
                        IdempotencyKeyModel,
                        extract("epoch", func.now() - IdempotencyKeyModel.created_at).label("age"),
                    ).where(IdempotencyKeyModel.key_hash == key_hash)
                )
            ).first()
            if row is None:  # deleted between the insert and the read: just take it
                await session.commit()
                return Claim("new")
            model, age = row
            if model.request_hash != request_hash:
                return Claim("mismatch")
            if model.state == "done":
                return Claim(
                    "replay",
                    Stored(
                        model.status_code or 200,
                        (model.response_body or "").encode(),
                        model.content_type or "",
                    ),
                )
            if age is not None and float(age) > _PENDING_STALE_SECONDS:
                # The first attempt died without finishing; let this one proceed.
                await session.execute(
                    update(IdempotencyKeyModel)
                    .where(IdempotencyKeyModel.key_hash == key_hash)
                    .values(created_at=func.now())
                )
                await session.commit()
                return Claim("new")
            return Claim("in_progress")

    async def complete(self, key_hash: str, stored: Stored) -> None:
        async with get_container().session_factory() as session:
            await session.execute(
                update(IdempotencyKeyModel)
                .where(IdempotencyKeyModel.key_hash == key_hash)
                .values(
                    state="done",
                    status_code=stored.status_code,
                    response_body=stored.body.decode("utf-8", errors="replace"),
                    content_type=stored.content_type,
                )
            )
            await session.commit()

    async def release(self, key_hash: str) -> None:
        async with get_container().session_factory() as session:
            await session.execute(delete(IdempotencyKeyModel).where(IdempotencyKeyModel.key_hash == key_hash))
            await session.commit()


def _problem(status: int, title: str, detail: str, error_code: str) -> tuple[int, bytes]:
    body = json.dumps(
        {
            "type": f"about:blank#{error_code}",
            "title": title,
            "status": status,
            "detail": detail,
            "error_code": error_code,
        }
    )
    return status, body.encode()


class IdempotencyMiddleware:
    def __init__(self, app: Callable[[Scope, Receive, Send], Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST" or not _PATH.match(scope["path"]):
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        raw_key = headers.get(HEADER)
        if not raw_key:
            await self.app(scope, receive, send)
            return

        key = raw_key.decode("latin-1").strip()
        if not key or len(key) > _MAX_KEY_LENGTH:
            await self._send_json(
                send,
                *_problem(422, "Invalid Idempotency-Key", "Use 1-100 characters.", "invalid_idempotency_key"),
            )
            return

        body, consumed = await self._read_body(receive)
        if body is None:  # too large to fingerprint (e.g. a file upload): not supported, run normally
            await self.app(scope, self._replay_consumed(consumed, receive), send)
            return

        principal = headers.get(b"authorization", b"")
        key_hash = hashlib.sha256(
            principal + b"|POST|" + scope["path"].encode() + b"|" + key.encode()
        ).hexdigest()
        request_hash = hashlib.sha256(body).hexdigest()
        store: IdempotencyStore = (
            getattr(scope["app"].state, "idempotency_store", None) or DatabaseIdempotencyStore()
        )

        try:
            claim = await store.claim(key_hash, request_hash)
        except Exception:  # noqa: BLE001 - never block a request because the key store is down
            logger.exception("Idempotency store unavailable; processing without it")
            await self.app(scope, self._replayable(body, receive), send)
            return

        if claim.outcome == "replay" and claim.stored is not None:
            await send(
                {
                    "type": "http.response.start",
                    "status": claim.stored.status_code,
                    "headers": [
                        (b"content-type", (claim.stored.content_type or "application/json").encode()),
                        (b"content-length", str(len(claim.stored.body)).encode()),
                        (b"idempotent-replay", b"true"),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": claim.stored.body})
            return
        if claim.outcome == "in_progress":
            await self._send_json(
                send,
                *_problem(
                    409,
                    "Request in progress",
                    "The first attempt is still running; retry shortly.",
                    "idempotency_in_progress",
                ),
            )
            return
        if claim.outcome == "mismatch":
            await self._send_json(
                send,
                *_problem(
                    422,
                    "Idempotency-Key reused",
                    "This key was already used with a different request.",
                    "idempotency_key_reused",
                ),
            )
            return

        status = 0
        content_type = ""
        chunks = bytearray()

        async def capture(message: MutableMapping[str, Any]) -> None:
            nonlocal status, content_type
            if message["type"] == "http.response.start":
                status = message["status"]
                for name, value in message.get("headers", []):
                    if name.lower() == b"content-type":
                        content_type = value.decode("latin-1")
            elif message["type"] == "http.response.body" and len(chunks) <= _MAX_STORED_RESPONSE_BYTES:
                chunks.extend(message.get("body", b""))
            await send(message)

        try:
            await self.app(scope, self._replayable(body, receive), capture)
        except BaseException:
            await self._safe(store.release(key_hash))
            raise

        if 200 <= status < 300 and len(chunks) <= _MAX_STORED_RESPONSE_BYTES:
            await self._safe(store.complete(key_hash, Stored(status, bytes(chunks), content_type)))
        else:
            await self._safe(store.release(key_hash))

    @staticmethod
    async def _safe(awaitable: Awaitable[None]) -> None:
        try:
            await awaitable
        except Exception:  # noqa: BLE001
            logger.exception("Could not update the idempotency record")

    @staticmethod
    async def _read_body(receive: Receive) -> tuple[bytes | None, list[MutableMapping[str, Any]]]:
        body = bytearray()
        consumed: list[MutableMapping[str, Any]] = []
        while True:
            message = await receive()
            consumed.append(message)
            body.extend(message.get("body", b""))
            if len(body) > _MAX_BODY_BYTES:
                return None, consumed
            if not message.get("more_body", False):
                return bytes(body), consumed

    @staticmethod
    def _replay_consumed(consumed: list[MutableMapping[str, Any]], receive: Receive) -> Receive:
        pending = list(consumed)

        async def replay() -> MutableMapping[str, Any]:
            if pending:
                return pending.pop(0)
            return await receive()

        return replay

    @staticmethod
    def _replayable(body: bytes, receive: Receive) -> Receive:
        sent = False

        async def replay() -> MutableMapping[str, Any]:
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        return replay

    @staticmethod
    async def _send_json(send: Send, status: int, body: bytes) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
