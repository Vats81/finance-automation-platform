"""A protocol-level probe of the configured database endpoint, for
/health?probe=db. It answers "where exactly does the connection fail?" from
inside the network the app actually runs in, which no outside tool can:

  1. TCP connect to host:port
  2. Postgres's SSLRequest: the server should answer 'S' (TLS ok), 'N'
     (no TLS) — an immediate close here means the endpoint drops us before
     TLS even starts
  3. TLS handshake itself (with SNI), reporting the negotiated version

It never authenticates and never sends credentials. The report is protocol
facts plus a truncated host hint, not the full hostname.
"""

import asyncio
import socket
import ssl
import struct

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

# Postgres wire protocol: length (8) + request code 80877103.
_SSL_REQUEST = struct.pack("!II", 8, 80877103)


def describe_host(host: str) -> dict[str, str]:
    """Kind + a short hint — enough to tell which database instance is
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


def _probe_sync(host: str, port: int, timeout: float) -> dict[str, str]:
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
        except Exception as exc:  # noqa: BLE001
            report["tls_handshake"] = f"failed: {type(exc).__name__}: {exc}"
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
    report.update(await asyncio.to_thread(_probe_sync, host, port, timeout))
    return report
