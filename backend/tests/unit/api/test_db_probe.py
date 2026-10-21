"""The /health?probe=db diagnostic, exercised against real local servers
that behave like each way a database endpoint can fail (or succeed), so
every branch of the probe is observed for real, not mocked. The servers are
plain threaded sockets so the tests don't depend on the Python version.
"""

import datetime
import socket
import ssl
import threading
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.api.db_probe import describe_host, probe_database_endpoint

Handler = Callable[[socket.socket], None]


@pytest.fixture
def serve() -> Iterator[Callable[[Handler], str]]:
    """Starts a one-connection TCP server running `handler`; yields a factory
    returning the DATABASE_URL to point the probe at.
    """
    listeners: list[socket.socket] = []

    def start(handler: Handler) -> str:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listeners.append(listener)

        def run() -> None:
            try:
                conn, _ = listener.accept()
            except OSError:
                return
            try:
                handler(conn)
            except OSError:
                pass
            finally:
                conn.close()

        threading.Thread(target=run, daemon=True).start()
        return f"postgresql+asyncpg://u:p@127.0.0.1:{listener.getsockname()[1]}/db"

    yield start
    for listener in listeners:
        listener.close()


def _read_ssl_request(conn: socket.socket) -> None:
    conn.settimeout(5)
    assert len(conn.recv(8)) == 8


async def test_refused_tcp_connection_is_reported() -> None:
    # Reserve a port, then close it so nothing is listening there.
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    report = await probe_database_endpoint(f"postgresql+asyncpg://u:p@127.0.0.1:{port}/db", timeout=2)

    assert report["tcp"].startswith("failed:")
    assert "sslrequest_reply" not in report


async def test_endpoint_that_drops_us_before_tls_is_identified(serve) -> None:
    # The suspected real-world case: the connection is closed right after
    # the SSLRequest, so the client never gets any reply.
    def drop(conn: socket.socket) -> None:
        _read_ssl_request(conn)

    report = await probe_database_endpoint(serve(drop), timeout=2)

    assert report["tcp"] == "ok"
    assert "dropped before TLS began" in report["sslrequest_reply"]
    assert "tls_handshake" not in report


async def test_server_that_refuses_tls_is_identified(serve) -> None:
    def refuse(conn: socket.socket) -> None:
        _read_ssl_request(conn)
        conn.sendall(b"N")

    report = await probe_database_endpoint(serve(refuse), timeout=2)

    assert report["sslrequest_reply"] == "N (server refuses TLS)"
    assert "tls_handshake" not in report


async def test_accepts_tls_but_handshake_fails(serve) -> None:
    # Says 'S' then hangs up instead of doing a TLS handshake.
    def accept_then_close(conn: socket.socket) -> None:
        _read_ssl_request(conn)
        conn.sendall(b"S")

    report = await probe_database_endpoint(serve(accept_then_close), timeout=2)

    assert report["sslrequest_reply"] == "S (server accepts TLS)"
    assert report["tls_handshake"].startswith("failed:")


def _self_signed_context(tmp_path: Path) -> ssl.SSLContext:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    cert_path, key_path = tmp_path / "cert.pem", tmp_path / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    return context


async def test_full_success_path_reports_the_tls_version(serve, tmp_path: Path) -> None:
    context = _self_signed_context(tmp_path)

    def tls_postgres(conn: socket.socket) -> None:
        _read_ssl_request(conn)
        conn.sendall(b"S")
        with context.wrap_socket(conn, server_side=True) as tls:
            tls.settimeout(2)
            try:
                tls.recv(1)  # hold the connection open until the probe hangs up
            except (OSError, ssl.SSLError):
                pass

    report = await probe_database_endpoint(serve(tls_postgres), timeout=5)

    assert report["tcp"] == "ok"
    assert report["sslrequest_reply"] == "S (server accepts TLS)"
    assert report["tls_handshake"].startswith("ok (TLSv1")


async def test_unparseable_url_is_reported_not_raised() -> None:
    assert await probe_database_endpoint("not a url at all") == {
        "error": "DATABASE_URL could not be parsed"
    }


@pytest.mark.parametrize(
    ("host", "kind"),
    [
        ("dpg-abc123xyz-a", "render-internal"),
        ("dpg-abc123xyz-a.oregon-postgres.render.com", "render-external"),
        ("localhost", "local"),
        ("db.example.com", "other"),
    ],
)
def test_describe_host_classifies_and_truncates(host: str, kind: str) -> None:
    described = describe_host(host)

    assert described["kind"] == kind
    # Never the full, directly-connectable hostname.
    assert len(described["hint"]) <= 13
    assert described["hint"] != host or len(host) <= 12


async def test_probe_never_includes_credentials() -> None:
    url = "postgresql+asyncpg://secretuser:secretpass@127.0.0.1:1/db"

    report = await probe_database_endpoint(url, timeout=2)

    assert "secretuser" not in str(report)
    assert "secretpass" not in str(report)
