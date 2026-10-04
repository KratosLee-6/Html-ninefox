"""End-to-end TLS proof: pinned fetch succeeds, SNI and cert use the hostname.

The socket-target gate spies on `socket.create_connection` and therefore
MISSES the defect that mattered most in v0.6.2: `conn.host` was reset to the
real name, which sends the *connect* back through DNS. That reset happens
after `create_connection` has already been called, so the spy recorded the
vetted IP and the gate went green on broken code.

What actually distinguishes the two cases is a successful TLS fetch against a
server whose certificate is issued for `localhost`, dialled through the
`localhost` hostname with `ips=["127.0.0.1"]`. The certificate only validates
if SNI and cert checking see the real hostname; the fetch only succeeds if
the socket went to the pinned address. Both halves of the fix are exercised,
and neither can be satisfied by a source-text assertion.
"""
from __future__ import annotations

import ipaddress
import ssl
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from htmlninefox import intake  # noqa: E402

SECRET = b"PRIVATE-NETWORK-SECRET"


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(SECRET)))
        self.end_headers()
        self.wfile.write(SECRET)

    def log_message(self, *a):
        pass


def _self_signed(tmp: Path, common_name: str = "pinned.example"):
    """A certificate for the requested name, generated in-process.

    `openssl` is not present on every Windows host, and a gate that quietly
    skips where a tool is missing is a gate that stops guarding.
    """
    import datetime

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    cert, key = tmp / f"cert-{common_name}.pem", tmp / "key.pem"
    if not cert.exists():
        key_obj = rsa.generate_private_key(public_exponent=65537,
                                           key_size=2048)
        name = x509.Name(
            [x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
        now = datetime.datetime.now(datetime.timezone.utc)
        cert_obj = (
            x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(key_obj.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=1))
            .add_extension(
                # Name only. If the certificate also covered 127.0.0.1 then a
                # fetcher that lost the hostname would still validate against
                # the address and the gate would pass on broken code — which
                # is exactly what happened on the first attempt at this test.
                x509.SubjectAlternativeName([
                    x509.DNSName(common_name),
                ]), critical=False)
            .sign(key_obj, hashes.SHA256())
        )
        key.write_bytes(key_obj.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()))
        cert.write_bytes(cert_obj.public_bytes(
            encoding=serialization.Encoding.PEM))
    return cert, key


def test_a_pinned_https_fetch_succeeds_with_real_sni_and_cert():
    """One request, both halves of the fix proven at once.

    The certificate is issued for `localhost` and the URL uses the `localhost`
    hostname, so the fetch can only succeed if the socket went to the pinned
    127.0.0.1 *and* the TLS layer was told the real name. Reverting
    `conn.host = host` breaks the socket half; dropping `server_hostname`
    breaks the TLS half. Neither can hide behind a passing signature check.
    """
    tmp = Path(__file__).parent / "cert"
    tmp.mkdir(parents=True, exist_ok=True)
    cert, key = _self_signed(tmp)

    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_ctx.load_cert_chain(str(cert), str(key))
    srv.socket = server_ctx.wrap_socket(srv.socket, server_side=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]

    client_ctx = ssl.create_default_context(cafile=str(cert))
    # The hostname must NOT resolve to the server, otherwise the two
    # implementations are indistinguishable: `localhost` already points at
    # 127.0.0.1, so a fetcher that dialed the hostname would still arrive and
    # the gate would pass on broken code.
    #
    # Instead: serve TLS on 127.0.0.1 but ask for a name that resolves to a
    # black-hole address. Only a fetcher that dials the VETTED IP can succeed;
    # one that re-resolves the name will time out. The certificate is issued
    # for that name, so the TLS half is exercised at the same time.
    seen: list[str] = []

    def _spy(address, *a, **kw):
        host = address[0]
        seen.append(host)
        # Whatever the caller asked for, only the vetted address answers.
        return _original_create(("127.0.0.1", address[1]), *a[1:], **kw)

    import socket as _socket_mod

    _original_create = _socket_mod.create_connection
    _socket_mod.create_connection = _spy
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        intake._PinnedHTTPSHandler(["127.0.0.1"], context=client_ctx),
        intake._NoRedirect)
    req = urllib.request.Request(
        f"https://pinned.example:{port}/", headers={"User-Agent": "probe"})
    try:
        response = opener.open(req, timeout=15)
        body = response.read()
        assert body == SECRET, f"unexpected body: {body[:40]!r}"
    finally:
        _socket_mod.create_connection = _original_create
        srv.shutdown()
        srv.server_close()

    # The connect must have been aimed at the vetted address, not the name.
    assert seen and seen[0] == "127.0.0.1", (
        f"connect target was {seen[:1]}, not the vetted address")
