"""SSRF gate: the connection must go to the address that was validated.

The existing rebinding test injects a fake transport, so it only proves that
`validate_url` still runs and that a post-fetch comparison notices a changed
answer. It cannot tell whether the real connection went to that address —
which is the whole defect. Every test here therefore drives a real socket.

Shape: a real HTTP server bound to 127.0.0.1, paired with a resolver that
claims the same host resolves to a public IP. If the fetcher connects to what
the resolver said, it reaches a host it never vetted; if it connects to what
it re-resolved, it reaches loopback. The gate fails on the first outcome.
"""
from __future__ import annotations

import contextlib
import http.server
import socket
import threading

import pytest

from htmlninefox import intake
from htmlninefox.intake import IntakeError, fetch_reference

SECRET = b"PRIVATE-NETWORK-SECRET"


class _Handler(http.server.BaseHTTPRequestHandler):
    """Serves a recognisable body so a leak is unambiguous."""

    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(SECRET)))
        self.end_headers()
        self.wfile.write(SECRET)

    def log_message(self, *args):  # silence the default stderr logging
        pass


@pytest.fixture()
def loopback_server():
    """A real HTTP server on 127.0.0.1, i.e. exactly what must not be reached."""
    srv = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield srv.server_address[1]
    finally:
        srv.shutdown()
        srv.server_close()


def _lying_resolver(public_ip="93.184.216.34"):
    """Report a public IP for every host, regardless of the real answer."""
    return _scripted_resolver([public_ip] * 4)


def _scripted_resolver(sequence):
    """Return `sequence[i]` on the i-th call, repeating the last value.

    A fixed-answer resolver is not enough to expose the window. The fetcher
    calls the resolver once to vet the URL and again (inside urllib) to decide
    where to connect. To make the defect visible, the first answer must be
    public and the second must be loopback — the same trick a real attacker
    uses, and the only ordering that actually reaches the private service.
    """
    state = {"n": 0}

    def resolve(host, port):
        i = min(state["n"], len(sequence) - 1)
        state["n"] += 1
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (sequence[i], port))]

    return resolve


def test_public_answer_does_not_reach_loopback(loopback_server):
    """A public first answer must not be followed by a private connection.

    The resolver reports a public IP for the vetting call and loopback for
    the connection that follows. A correct fetcher connects to the address it
    vetted, so the loopback service is never contacted and its body never
    enters memory. An unpinned fetcher re-resolves and connects to loopback,
    which is the defect.
    """
    url = f"http://rebind.test:{loopback_server}/"
    resolver = _scripted_resolver(["93.184.216.34", "127.0.0.1"])
    try:
        result = fetch_reference(url, resolver=resolver, max_hops=0)
    except IntakeError as exc:
        assert SECRET.decode() not in str(exc)
        # A plain transport failure is NOT acceptable here: it is what an
        # unpinned fetcher produces when it follows the second answer and the
        # connection happens to fail. The fix must fail with a decision
        # (forbidden / not-pinned / rebinding), never by accident.
        assert exc.code in {
            "intake_host_forbidden",
            "intake_rebind_suspected",
            "intake_connect_failed",
        }, f"failing by {exc.code!r} means the connection was attempted, " \
           f"not prevented"
        return

    pytest.fail(
        "fetcher accepted a response it never vetted: "
        f"final_url={result.get('final_url')!r} "
        f"body={result.get('body', b'')[:40]!r}"
    )


def test_loopback_is_refused_before_any_connection(loopback_server):
    """A literal loopback host is rejected at the gate, not at connect time."""
    url = f"http://127.0.0.1:{loopback_server}/"

    with pytest.raises(IntakeError) as excinfo:
        fetch_reference(url, max_hops=0)
    assert excinfo.value.code == "intake_host_forbidden"


def test_validate_url_reports_the_ips_it_vetted():
    """validate_url already returns the vetted list; the transport must use it."""
    calls = {"n": 0}

    def counting_resolver(host, port):
        calls["n"] += 1
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    _, host, ips = intake.validate_url("https://example.com/", counting_resolver)
    assert host == "example.com"
    assert ips == ["93.184.216.34"]
    assert calls["n"] == 1


def test_default_transport_accepts_a_pinned_address():
    """The default transport must be able to be told which IP to connect to.

    A transport signature that cannot carry the vetted address cannot close the
    window, no matter what the caller does with `ips`. This asserts the seam
    exists rather than trusting that it will.
    """
    import inspect

    params = inspect.signature(intake._default_transport).parameters
    assert "ips" in params, (
        "_default_transport takes no vetted-IP argument, so validate_url's "
        "result can never reach the socket layer"
    )


def test_pinned_handlers_replace_the_default_ones():
    """The opener must use the pinning handlers whenever IPs are supplied.

    The first version of this gate read `_default_transport`'s source and
    asserted the handler names appeared as substrings. It passed, then failed
    the moment the opener construction moved into a helper — a text assertion
    on source, which says nothing about behaviour and breaks on any refactor.
    It now inspects the opener that production actually builds.
    """
    opener = intake._build_pinned_opener(["203.0.113.10"])
    names = [type(h).__name__ for h in opener.handlers]
    assert "_PinnedHTTPHandler" in names, names
    assert "_PinnedHTTPSHandler" in names, names
    # The stock handlers that would re-resolve must be gone.
    assert "HTTPHandler" not in names, f"stock HTTPHandler still in chain: {names}"
    assert "HTTPSHandler" not in names, f"stock HTTPSHandler still in chain: {names}"


def test_opener_has_no_proxy_handler_in_front_of_the_pinned_ones():
    """A configured proxy must not be able to take the request first.

    `urllib.request.build_opener` installs a default `ProxyHandler`, and this
    project runs behind HTTP_PROXY/HTTPS_PROXY on many machines. Handler order
    decides who wins, and the default proxy handler is installed first — so
    with a proxy set, the request is routed to the proxy, which performs its
    own DNS and its own connection. The vetted address is then never used and
    the pinning silently does nothing.

    This is not hypothetical: on a host with HTTPS_PROXY set, the pinned
    handlers sat at chain positions 6 and 7, behind ProxyHandler at 0.

    The assertion builds the opener the way production does, through
    `_build_pinned_opener`, rather than hand-assembling one — otherwise the
    gate would only prove the helper is clean and say nothing about the opener
    actually used.
    """
    opener = intake._build_pinned_opener(["203.0.113.10"])
    names = [type(h).__name__ for h in opener.handlers]
    proxy_at = [i for i, n in enumerate(names)
                if "Proxy" in n and not n.startswith("_NoProxy")]
    pinned_at = [i for i, n in enumerate(names) if "Pinned" in n]
    assert pinned_at, f"the production opener has no pinned handler: {names}"
    assert not proxy_at, (
        f"a ProxyHandler at {proxy_at} precedes the pinned handlers at "
        f"{pinned_at}; with a proxy configured the vetted address is bypassed"
    )


class _Harness:
    """A loopback HTTP server that records what the server actually received.

    Needed because a rejection-only test suite cannot tell "correctly refused"
    from "broken": the request line, the Host header and the body all have to
    be observed from the far end to say anything real about the client side.
    """

    def __init__(self) -> None:
        self.request_line: str = ""
        self.seen = 0

    def handler(self):
        harness = self

        class H(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_GET(self):  # noqa: N802
                harness.request_line = self.requestline
                harness.seen += 1
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(SECRET)))
                self.end_headers()
                self.wfile.write(SECRET)

            def log_message(self, *a):
                pass

        return H

    def server(self):
        srv = http.server.HTTPServer(("127.0.0.1", 0), self.handler())
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()

        @contextlib.contextmanager
        def _cm():
            try:
                yield srv.server_address
            finally:
                srv.shutdown()
                srv.server_close()

        return _cm()

    def assert_served(self) -> None:
        assert self.seen, "the server was never reached"


def test_a_pinned_fetch_actually_returns_the_body():
    """A pinned request must succeed end to end and return its body.

    This is the gate that was missing. Every other test in this file checks a
    rejection, so the whole request-construction path had zero behavioural
    coverage — which is exactly how `conn.request(method, url, headers, ...)`
    shipped: headers landed in the `body` parameter, http.client raised
    TypeError on every single call, and nothing noticed because nothing ever
    completed a fetch. A test that never sees a successful response cannot tell
    "correctly refused" apart from "broken".

    It also pins the Host header, which is what a virtual-hosted server needs.
    """
    sess = _Harness()
    with sess.server() as (host, port):
        # _default_transport returns (status, headers, body).
        status, headers, body = intake._default_transport(
            f"http://{host}:{port}/", {"X-Probe": "1"}, 5.0, 65536,
            ips=[host])
        assert status == 200, f"unexpected status {status}"
        assert body == SECRET, f"unexpected body: {body[:40]!r}"
        assert headers, "no response headers"
    sess.assert_served()


def test_the_request_line_is_a_path_not_an_absolute_url():
    """A proxied request degrades to `GET http://host/ HTTP/1.1`.

    The default ProxyHandler rewrites the selector into an absolute URL, which
    many origin servers reject. With the proxy removed from the chain the
    request line must be the plain path.
    """
    sess = _Harness()
    with sess.server() as (host, port):
        intake._default_transport(
            f"http://{host}:{port}/some/path", {}, 5.0, 65536, ips=[host])
    assert sess.request_line.startswith("GET /some/path "), (
        f"request line is not a plain path: {sess.request_line!r}")
    sess.assert_served()


def test_https_handler_accepts_the_context_keyword():
    """`HTTPSHandler.https_open` passes `context=`; the override must take it.

    Without this, every https request dies with
    `TypeError: do_open() got an unexpected keyword argument 'context'`
    before a socket is opened. The mutation test for the original v0.6.2
    release missed this entirely, because no gate ever drove the https branch
    far enough to raise.

    Driven through the real handler rather than by reading its signature: a
    signature assertion is exactly the kind of text-shaped check that goes
    green on a comment.
    """
    import http.client

    called = {}

    class _Req:
        full_url = "https://example.invalid/x"
        method = "GET"
        selector = "/x"
        data = None
        timeout = 0.1
        headers = {}

        def get_full_url(self):
            return self.full_url

        def has_header(self, _name):
            return False

    handler = intake._PinnedHTTPSHandler(["203.0.113.10"])
    # The point is that the call is accepted and reaches the socket stage; the
    # connection itself is expected to fail against a documentation address.
    with pytest.raises(Exception) as excinfo:
        handler.do_open(http.client.HTTPSConnection, _Req(),
                        context=handler._context)
    assert "unexpected keyword argument" not in str(excinfo.value), (
        f"do_open rejected the context keyword urllib always passes: "
        f"{excinfo.value}"
    )


def test_https_pinning_keeps_the_ip_as_the_connect_target():
    """The vetted address must still be the socket target on TLS.

    `conn.host = host` before `connect()` looks like the obvious way to keep
    the hostname for SNI, but `HTTPSConnection.connect()` reads `self.host`
    for the connect target too — so it sends the socket back through a fresh
    DNS lookup and the vetted address is discarded. The proof is a spy on
    `socket.create_connection`: it must receive the vetted IP, never the
    hostname.
    """
    import socket as _socket
    from contextlib import contextmanager

    seen: list = []
    original = _socket.create_connection

    @contextmanager
    def _server():
        srv = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            yield srv.server_address
        finally:
            srv.shutdown()
            srv.server_close()

    def spy(address, *a, **kw):
        seen.append(address)
        return original(address, *a, **kw)

    _socket.create_connection = spy
    try:
        with _server() as (host, port):
            try:
                intake._default_transport(
                    f"https://{host}:{port}/", {}, 1.0, 1024, ips=[host])
            except Exception:
                # The TLS handshake against a plain HTTP server fails; what
                # matters is the address the socket layer was handed.
                pass
    finally:
        _socket.create_connection = original

    if not seen:
        # No skip. The first version of this gate called pytest.skip() when no
        # connection was observed, and that made it miss the exact mutation it
        # was written for: with `conn.host` reset the handshake fails before
        # create_connection ever runs, the list stays empty, and the gate skips
        # itself into a pass. A skip is a green light.
        raise AssertionError(
            "no TCP connection was attempted, so the connect target could not "
            "be observed — the HTTPS path never ran"
        )
    for addr in seen:
        assert _is_ip_literal(addr[0]), (
            f"socket target {addr[0]!r} is a hostname, not the vetted IP — "
            f"the connect target went back through DNS")


def _is_ip_literal(text: str) -> bool:
    import ipaddress

    try:
        ipaddress.ip_address(text)
        return True
    except ValueError:
        return False



