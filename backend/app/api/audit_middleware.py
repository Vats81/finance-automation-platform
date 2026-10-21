"""Audit trail for business-scoped mutations.

A pure-ASGI middleware (not BaseHTTPMiddleware, which can't see the final
status and body together without buffering everything). It records one row,
after the response has been produced, for every *successful* POST/PUT/PATCH/
DELETE that passed the business role check: actor, role, business, the route
template that ran, the affected record and the status. Request and response
payloads are never stored. Audit failures are logged and swallowed: they must
never turn a successful financial change into an error.
"""

import json
import logging
import re
import uuid
from collections.abc import Awaitable, Callable, MutableMapping
from dataclasses import dataclass
from typing import Any

from app.audit.infrastructure.models import BusinessAuditEventModel
from app.bootstrap.container import get_container

logger = logging.getLogger(__name__)

Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]

_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}
_MAX_BODY_BYTES = 64 * 1024
_PARAM = re.compile(r"\{(\w+)\}")


@dataclass(frozen=True)
class AuditEvent:
    business_id: uuid.UUID
    actor_user_id: uuid.UUID
    actor_role: str
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    status_code: int


AuditRecorder = Callable[[AuditEvent], Awaitable[None]]


async def record_to_database(event: AuditEvent) -> None:
    async with get_container().session_factory() as session:
        session.add(
            BusinessAuditEventModel(
                id=uuid.uuid4(),
                business_id=event.business_id,
                actor_user_id=event.actor_user_id,
                actor_role=event.actor_role,
                action=event.action,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                status_code=event.status_code,
            )
        )
        await session.commit()


def _as_uuid(value: Any) -> uuid.UUID | None:
    try:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def describe(route_path: str, path_params: dict[str, Any], body: bytes) -> tuple[str, uuid.UUID | None]:
    """(entity type, entity id) for a route template like
    /businesses/{business_id}/sales/{sale_id}/void.
    """
    template = route_path.removeprefix("/api/v1")
    params = [p for p in _PARAM.findall(template) if p != "business_id"]
    if params:
        name = params[-1]
        return name.removesuffix("_id"), _as_uuid(path_params.get(name))

    # A create: the new record's id is in the response body.
    segments = [s for s in template.split("/") if s and not s.startswith("{")]
    entity_type = segments[-1] if segments else "business"
    try:
        parsed = json.loads(body) if body else None
    except ValueError:
        parsed = None
    new_id = _as_uuid(parsed.get("id")) if isinstance(parsed, dict) else None
    return entity_type, new_id


class AuditMiddleware:
    def __init__(self, app: Callable[[Scope, Receive, Send], Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in _MUTATING:
            await self.app(scope, receive, send)
            return

        status = 0
        body = bytearray()

        async def capture(message: MutableMapping[str, Any]) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            elif message["type"] == "http.response.body" and len(body) < _MAX_BODY_BYTES:
                body.extend(message.get("body", b"")[: _MAX_BODY_BYTES - len(body)])
            await send(message)

        await self.app(scope, receive, capture)

        try:
            await self._audit(scope, status, bytes(body))
        except Exception:  # noqa: BLE001 - auditing must never break a request
            logger.exception("Could not write audit event")

    async def _audit(self, scope: Scope, status: int, body: bytes) -> None:
        state = scope.get("state") or {}
        actor_id = state.get("audit_actor_id")
        business_id = state.get("audit_business_id")
        route = scope.get("route")
        if not (200 <= status < 300) or actor_id is None or business_id is None or route is None:
            return

        entity_type, entity_id = describe(route.path, scope.get("path_params") or {}, body)
        event = AuditEvent(
            business_id=business_id,
            actor_user_id=actor_id,
            actor_role=state.get("audit_role", "unknown"),
            action=f"{scope['method']} {route.path.removeprefix('/api/v1')}"[:255],
            entity_type=entity_type[:60],
            entity_id=entity_id,
            status_code=status,
        )
        recorder: AuditRecorder = getattr(scope["app"].state, "audit_recorder", record_to_database)
        await recorder(event)
