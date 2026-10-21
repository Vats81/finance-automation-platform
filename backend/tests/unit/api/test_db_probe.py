"""The /health?probe=db diagnostic, exercised against real local servers
that behave like each way a database endpoint can fail (or succeed), so
every branch of the probe is observed for real, not mocked. The servers are
plain threaded sockets so the tests don't depend on the Python version.
"""

import datetime
import socket
import ssl
import struct
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


def _tls_postgres(
    serve,
    tmp_path: Path,
    on_startup: Callable[[ssl.SSLSocket, bytes], None],
    user: str = "bob",
    db: str = "shop",
) -> str:
    """A server that says 'S', completes a real TLS handshake, reads the
    client's startup message, then lets `on_startup` play the server's reply.
    Returns the DATABASE_URL to probe (carrying the given user and database).
    """
    context = _self_signed_context(tmp_path)

    def handler(conn: socket.socket) -> None:
        _read_ssl_request(conn)
        conn.sendall(b"S")
        with context.wrap_socket(conn, server_side=True) as tls:
            tls.settimeout(3)
            try:
                on_startup(tls, tls.recv(4096))
            except (OSError, ssl.SSLError):
                pass

    url = serve(handler)
    return url.replace("u:p@", f"{user}:secretpw@").rsplit("/", 1)[0] + f"/{db}"


def _error_message(severity: str, code: str, message: str) -> bytes:
    body = b"S" + severity.encode() + b"\x00C" + code.encode() + b"\x00M" + message.encode() + b"\x00\x00"
    return b"E" + struct.pack("!I", len(body) + 4) + body


async def test_live_server_asking_for_a_password_is_reported_alive(serve, tmp_path: Path) -> None:
    seen: list[bytes] = []

    def reply_md5(tls: ssl.SSLSocket, startup: bytes) -> None:
        seen.append(startup)
        tls.sendall(b"R" + struct.pack("!III", 12, 5, 0x01020304))  # AuthenticationMD5Password

    report = await probe_database_endpoint(_tls_postgres(serve, tmp_path, reply_md5), timeout=5)

    assert report["tcp"] == "ok"
    assert report["sslrequest_reply"] == "S (server accepts TLS)"
    assert report["tls_handshake"].startswith("ok (TLSv1")
    assert report["startup_reply"] == (
        "R: server requests authentication (md5 password) - it is alive and talking"
    )
    # What the probe sent: the protocol 3.0 startup message with the user and
    # database name — and no password, ever.
    assert seen[0][4:8] == b"\x00\x03\x00\x00"
    assert b"user\x00bob\x00database\x00shop\x00" in seen[0]
    assert b"secretpw" not in seen[0]


async def test_server_error_text_is_reported_with_user_db_and_ip_redacted(serve, tmp_path: Path) -> None:
    def reply_error(tls: ssl.SSLSocket, startup: bytes) -> None:
        tls.sendall(
            _error_message(
                "FATAL",
                "28000",
                'no pg_hba.conf entry for host "10.9.8.7", user "bob", database "shop", SSL encryption',
            )
        )

    report = await probe_database_endpoint(_tls_postgres(serve, tmp_path, reply_error), timeout=5)

    reply = report["startup_reply"]
    assert reply.startswith("E: FATAL 28000 no pg_hba.conf entry for host")
    assert '"<ip>"' in reply and '"<user>"' in reply and '"<database>"' in reply
    for leaked in ("10.9.8.7", "bob", "shop", "secretpw"):
        assert leaked not in str(report)


async def test_proxy_that_hangs_up_after_tls_is_distinguished_from_a_postgres_error(
    serve, tmp_path: Path
) -> None:
    # The suspected real-world case: TLS works, then the connection is
    # closed before Postgres ever answers.
    def hang_up(tls: ssl.SSLSocket, startup: bytes) -> None:
        return None

    report = await probe_database_endpoint(_tls_postgres(serve, tmp_path, hang_up), timeout=5)

    assert report["tls_handshake"].startswith("ok (TLSv1")
    assert report["startup_reply"] == (
        "connection closed with no reply (dropped after TLS, before the server answered)"
    )


async def test_unexpected_message_type_is_reported(serve, tmp_path: Path) -> None:
    def reply_odd(tls: ssl.SSLSocket, startup: bytes) -> None:
        tls.sendall(b"Z" + struct.pack("!IB", 5, 73))

    report = await probe_database_endpoint(_tls_postgres(serve, tmp_path, reply_odd), timeout=5)

    assert report["startup_reply"] == "unexpected message type b'Z'"


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
