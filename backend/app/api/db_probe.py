"""A protocol-level probe of the configured database endpoint, for
/health?probe=db. It answers "where exactly does the connection fail?" from
inside the network the app actually runs in, which no outside tool can:

  1. TCP connect to host:port
  2. Postgres's SSLRequest: the server should answer 'S' (TLS ok), 'N'
     (no TLS) - an immediate close here means the endpoint drops us before
     TLS even starts
  3. TLS handshake itself (with SNI), reporting the negotiated version
  4. Postgres's startup message (username + database name, NO password). A
     live server answers with an authentication request or its own error
     text; a proxy/firewall or a dead instance just hangs up. That
     difference is what separates "the database refused us" from "something
     in front of the database dropped us".

It never authenticates and never sends a password. The report is protocol
facts plus a truncated host hint, not the full hostname; the username,
database name and any IP addresses are redacted from server error text.
"""

import asyncio
import re
import socket
import ssl
import struct

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

# Postgres wire protocol: length (8) + request code 80877103.
_SSL_REQUEST = struct.pack("!II", 8, 80877103)
_PROTOCOL_3_0 = 196608
_NUL = b"\x00"
_IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
_AUTH_TYPES = {
    0: "ok",
    2: "kerberos",
    3: "cleartext password",
    5: "md5 password",
    10: "scram-sha-256 (SASL)",
}


def _startup_message(user: str, database: str) -> bytes:
    params = b"user" + _NUL + user.encode() + _NUL + b"database" + _NUL + database.encode() + _NUL + _NUL
    body = struct.pack("!I", _PROTOCOL_3_0) + params
    return struct.pack("!I", len(body) + 4) + body


def _redact(text: str, user: str, database: str) -> str:
    for secret, label in ((user, "<user>"), (database, "<database>")):
        if secret:
            text = text.replace(secret, label)
    return _IPV4.sub("<ip>", text)


def _recv_exact(sock: socket.socket, count: int) -> bytes:
    data = b""
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            raise EOFError
        data += chunk
    return data


def _describe_startup_reply(tls: socket.socket, user: str, database: str) -> str:
    try:
        kind = _recv_exact(tls, 1)
        length = struct.unpack("!I", _recv_exact(tls, 4))[0]
        payload = _recv_exact(tls, min(max(length - 4, 0), 4096))
    except (EOFError, ConnectionError):
        return "connection closed with no reply (dropped after TLS, before the server answered)"
    except Exception as exc:  # noqa: BLE001 - diagnostic: report, don't raise
        return f"failed: {type(exc).__name__}: {exc}"

    if kind == b"R":
        code = struct.unpack("!I", payload[:4])[0] if len(payload) >= 4 else -1
        auth = _AUTH_TYPES.get(code, f"type {code}")
        return f"R: server requests authentication ({auth}) - it is alive and talking"
    if kind == b"E":
        fields: dict[str, str] = {}
        for part in payload.split(_NUL):
            if len(part) > 1:
                fields[chr(part[0])] = part[1:].decode("utf-8", "replace")
        message = _redact(fields.get("M", ""), user, database)
        return f"E: {fields.get('S', 'ERROR')} {fields.get('C', '')} {message}".strip()
    return f"unexpected message type {kind!r}"


def describe_host(host: str) -> dict[str, str]:
    """Kind + a short hint - enough to tell which database instance is
    configured (compare with the Render dashboard) without printing the
    full, directly-connectable hostname.
    """
    if host.startswith("dpg-") and "." not in host:
        kind = "render-internal"
    elif host.endswith(".render.com"):
        kind = "render-external"
    elif host in {"localhost", "127.0.0.1", "::1"}:
        kind = "local"
    else:
        kind = "other"
    return {"kind": kind, "hint": host[:12] + ("…" if len(host) > 12 else "")}


def _probe_sync(host: str, port: int, timeout: float, user: str, database: str) -> dict[str, str]:
    # Plain sockets + the stdlib ssl module rather than asyncio streams:
    # StreamWriter.start_tls only exists on Python 3.11+, and a diagnostic
    # that only works on one interpreter version is useless when it's needed.
    report: dict[str, str] = {}
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - diagnostic: report, don't raise
        report["tcp"] = f"failed: {type(exc).__name__}: {exc}"
        return report
    report["tcp"] = "ok"

    try:
        sock.settimeout(timeout)
        sock.sendall(_SSL_REQUEST)
        try:
            reply = sock.recv(1)
        except Exception as exc:  # noqa: BLE001
            report["sslrequest_reply"] = f"failed: {type(exc).__name__}: {exc}"
            return report

        if reply == b"":
            report["sslrequest_reply"] = "connection closed with no reply (dropped before TLS began)"
            return report
        report["sslrequest_reply"] = {b"S": "S (server accepts TLS)", b"N": "N (server refuses TLS)"}.get(
            reply, f"unexpected byte {reply!r}"
        )
        if reply != b"S":
            return report

        # Same posture as sslmode=require: encrypt, don't verify the cert.
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        try:
            with context.wrap_socket(sock, server_hostname=host) as tls:
                report["tls_handshake"] = f"ok ({tls.version() or 'unknown version'})"
                tls.sendall(_startup_message(user, database))
                report["startup_reply"] = _describe_startup_reply(tls, user, database)
        except Exception as exc:  # noqa: BLE001
            report.setdefault("tls_handshake", f"failed: {type(exc).__name__}: {exc}")
        return report
    finally:
        sock.close()


async def probe_database_endpoint(database_url: str, *, timeout: float = 6.0) -> dict[str, str]:
    try:
        url = make_url(database_url)
    except ArgumentError:
        return {"error": "DATABASE_URL could not be parsed"}

    host, port = url.host or "", url.port or 5432
    described = describe_host(host)
    report = {"host_kind": described["kind"], "host_hint": described["hint"], "port": str(port)}
    user, database = url.username or "postgres", url.database or "postgres"
    report.update(await asyncio.to_thread(_probe_sync, host, port, timeout, user, database))
    return report
