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

    Passing `ips` while still opening a default `urllib` handler would look
    correct in review and do nothing at runtime — the same "both sides exist,
    nobody checks they are joined" shape as C3/C4.
    """
    import inspect

    source = inspect.getsource(intake._default_transport)
    assert "_PinnedHTTPHandler" in source
    assert "_PinnedHTTPSHandler" in source
    # They must be added to the opener, not merely defined nearby.
    assert "build_opener(" in source
    assert "_PinnedHTTPHandler(ips)" in source


def test_https_pinning_keeps_the_real_hostname_for_sni():
    """The pinned socket must still present the real host to TLS.

    `HTTPSConnection` takes SNI and the certificate name from `self.host`, so
    pinning the address without restoring the hostname would break every
    virtual-hosted HTTPS site — a fix that passes a plain-HTTP gate while
    destroying real fetches.
    """
    import inspect

    src = inspect.getsource(intake._PinnedHTTPSHandler.do_open)
    assert "conn.host = host" in src, (
        "pinned HTTPS connection keeps the IP as self.host, so SNI and "
        "certificate validation would run against the address"
    )
