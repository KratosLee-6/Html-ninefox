"""v0.6 Phase 1: safe design-intake fetching (SSRF gate, redirects, evidence)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from htmlninefox import intake
from htmlninefox.intake import IntakeError, RateLimiter, fetch_reference, load_sources, save_evidence, validate_url

PUBLIC = {"example.com": ["93.184.216.34"], "cdn.example.com": ["93.184.216.34"]}
FORBIDDEN_HOSTS = {
    "localhost": ["127.0.0.1"],
    "metadata.internal": ["169.254.169.254"],
    "lan.host": ["192.168.1.10"],
    "nat.host": ["10.0.0.7"],
    "sitehost": ["172.16.0.5"],
    "v6host": ["fd00::1"],
    "zero": ["0.0.0.0"],
}
RESOLVER_TABLE = {**PUBLIC, **FORBIDDEN_HOSTS}


def resolver(host, port):
    ips = RESOLVER_TABLE.get(host)
    if ips is None:
        raise OSError(f"unknown host {host}")
    return [(2, 1, 6, "", (ip, port)) for ip in ips]


def ok_transport(body: bytes = b"<html>ok</html>", content_type: str = "text/html"):
    def transport(url, headers, timeout, max_bytes):
        return 200, {"content-type": content_type}, body
    return transport


# ---------------------------------------------------------------- URL gate


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "ftp://example.com/x",
    "javascript:alert(1)",
])
def test_rejects_non_http_schemes(url):
    with pytest.raises(IntakeError) as excinfo:
        validate_url(url, resolver)
    assert excinfo.value.code == "intake_scheme_invalid"


@pytest.mark.parametrize("host", list(FORBIDDEN_HOSTS))
def test_rejects_private_loopback_and_reserved_hosts(host):
    with pytest.raises(IntakeError) as excinfo:
        validate_url(f"https://{host}/page", resolver)
    assert excinfo.value.code == "intake_host_forbidden"


def test_rejects_unresolvable_host():
    with pytest.raises(IntakeError) as excinfo:
        validate_url("https://missing.example/page", resolver)
    assert excinfo.value.code == "intake_host_unresolved"


def test_accepts_public_host():
    scheme, host, ips = validate_url("https://example.com/page", resolver)
    assert (scheme, host, ips) == ("https", "example.com", ["93.184.216.34"])


# ---------------------------------------------------------------- fetching


def test_fetch_returns_evidence():
    calls = []

    def transport(url, headers, timeout, max_bytes):
        calls.append(url)
        return 200, {"content-type": "text/html; charset=utf-8"}, b"<html>hello intake</html>"

    evidence = fetch_reference("https://example.com/page", transport=transport, resolver=resolver)
    assert evidence["final_url"] == "https://example.com/page"
    assert evidence["status"] == 200
    assert evidence["body_bytes"] == len(b"<html>hello intake</html>")
    assert evidence["content_type"].startswith("text/html")
    assert len(evidence["body_sha256"]) == 64
    assert calls == ["https://example.com/page"]


def test_fetch_follows_redirects_within_public_hosts():
    def transport(url, headers, timeout, max_bytes):
        if url == "https://example.com/old":
            return 301, {"location": "https://cdn.example.com/new"}, b""
        return 200, {"content-type": "text/html"}, b"landed"

    evidence = fetch_reference("https://example.com/old", transport=transport, resolver=resolver)
    assert evidence["final_url"] == "https://cdn.example.com/new"
    assert evidence["followed"] == ["https://example.com/old", "https://cdn.example.com/new"]


def test_fetch_rejects_redirect_into_private_host():
    def transport(url, headers, timeout, max_bytes):
        return 302, {"location": "https://metadata.internal/latest"}, b""

    with pytest.raises(IntakeError) as excinfo:
        fetch_reference("https://example.com/jump", transport=transport, resolver=resolver)
    assert excinfo.value.code == "intake_host_forbidden"


def test_fetch_rejects_redirect_chain_overflow():
    def transport(url, headers, timeout, max_bytes):
        return 302, {"location": f"https://example.com/hop{len(url)}"}, b""

    with pytest.raises(IntakeError) as excinfo:
        fetch_reference("https://example.com/loop", transport=transport, resolver=resolver, max_hops=2)
    assert excinfo.value.code == "intake_too_many_redirects"


def test_fetch_detects_dns_rebinding():
    calls = {"count": 0}

    def rebinding_resolver(host, port):
        calls["count"] += 1
        ips = PUBLIC[host] if calls["count"] % 2 else ["127.0.0.1"]
        return [(2, 1, 6, "", (ips[0], port))]

    with pytest.raises(IntakeError) as excinfo:
        fetch_reference("https://example.com/", transport=ok_transport(), resolver=rebinding_resolver)
    assert excinfo.value.code == "intake_rebind_suspected"


def test_fetch_enforces_size_cap():
    big = b"x" * 5000
    with pytest.raises(IntakeError) as excinfo:
        fetch_reference("https://example.com/big", transport=ok_transport(big),
                        resolver=resolver, max_bytes=1024)
    assert excinfo.value.code == "intake_too_large"


def test_fetch_reports_http_errors_stably():
    def transport(url, headers, timeout, max_bytes):
        raise IntakeError("intake_fetch_failed", "远端返回 HTTP 404", 502)

    with pytest.raises(IntakeError) as excinfo:
        fetch_reference("https://example.com/missing", transport=transport, resolver=resolver)
    assert excinfo.value.code == "intake_fetch_failed"


# ---------------------------------------------------------------- evidence store


def test_save_evidence_writes_meta_and_body(tmp_path: Path) -> None:
    evidence = fetch_reference("https://example.com/inspo", transport=ok_transport(), resolver=resolver)
    target = save_evidence(tmp_path, "land-book", evidence)

    assert target.is_dir()
    meta = json.loads((target / "meta.json").read_text(encoding="utf-8"))
    assert meta["final_url"] == "https://example.com/inspo"
    assert meta["body_sha256"] == evidence["body_sha256"]
    assert (target / "body.html").read_bytes() == b"<html>ok</html>"
    assert "intake" in str(target)


# ---------------------------------------------------------------- source registry


def test_load_sources_reads_builtin_registry() -> None:
    sources = load_sources()
    ids = {source["id"] for source in sources}
    assert {"land-book", "godly", "codrops"} <= ids
    for source in sources:
        assert source["license_class"] in intake.LICENSE_CLASSES
        assert source["entry_url"].startswith("https://")


def test_user_source_overrides_builtin_by_id(tmp_path: Path) -> None:
    override = tmp_path / "design-galleries.yaml"
    override.write_text(
        "sources:\n  - id: land-book\n    name: 自定义覆盖\n    kind: gallery\n"
        "    license_class: open\n    entry_url: https://example.org/land-book\n",
        encoding="utf-8",
    )
    sources = load_sources(extra_dir=tmp_path)
    land_book = next(source for source in sources if source["id"] == "land-book")
    assert land_book["name"] == "自定义覆盖"
    assert land_book["license_class"] == "open"


def test_invalid_source_is_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "sources:\n  - id: broken\n    name: x\n    kind: gallery\n"
        "    license_class: public-domain\n    entry_url: https://example.org\n",
        encoding="utf-8",
    )
    with pytest.raises(IntakeError):
        load_sources(extra_dir=tmp_path)


# ---------------------------------------------------------------- rate limiting


def test_rate_limiter_enforces_interval_per_key() -> None:
    now = {"t": 100.0}

    def clock():
        return now["t"]

    limiter = RateLimiter(default_interval=5.0, clock=clock,
                          sleep=lambda seconds: now.__setitem__("t", now["t"] + seconds))
    assert limiter.wait("a") == 0.0
    assert now["t"] == 100.0
    assert limiter.wait("a") == 5.0  # 第二次同 key：预约下一个可用点并等待
    assert now["t"] == 105.0
    assert limiter.wait("b") == 0.0  # 不同 key 不互相影响
    assert now["t"] == 105.0


# ---------------------------------------------------------------- candidate extraction

from htmlninefox.intake import CandidateStore, extract_candidate  # noqa: E402

SAMPLE_HTML = b"""<!doctype html><html><head><title>Acme Pricing Page</title>
<style>body{color:#173C8F;font-family:'Inter',sans-serif}
.badge{background:rgba(73,184,148,.2)}</style></head>
<body><nav></nav><header><h1>Simple pricing</h1></header>
<main><section><h2>Plans</h2><a href="#">buy</a><img src="a.png"></section>
<section><h2>FAQ</h2></section></main><footer></footer></body></html>"""


def html_evidence(body: bytes = SAMPLE_HTML, url: str = "https://example.com/pricing") -> dict:
    return {
        "url": url, "final_url": url, "followed": [url], "status": 200,
        "content_type": "text/html; charset=utf-8", "body": body,
        "body_sha256": "0" * 64, "body_bytes": len(body),
        "fetched_at": "2026-09-26T10:00:00",
    }


def test_extract_candidate_builds_skeleton_and_tokens() -> None:
    source = {"id": "land-book", "license_class": "reference"}
    candidate = extract_candidate(html_evidence(), source=source)
    assert candidate["candidate_id"].startswith("example.com")
    assert candidate["title"] == "Acme Pricing Page"
    assert candidate["status"] == "pending"
    assert candidate["license_class"] == "reference"
    assert candidate["tokens"]["colors"][:2] == ["#173C8F", "rgba(73,184,148,.2)"]
    assert "Inter" in candidate["tokens"]["fonts"]
    assert candidate["skeleton"]["semantic"]["nav"] == 1
    assert candidate["skeleton"]["semantic"]["section"] == 2
    assert [h["text"] for h in candidate["skeleton"]["headings"]] == ["Simple pricing", "Plans", "FAQ"]


def test_extract_candidate_guesses_intent() -> None:
    candidate = extract_candidate(html_evidence())
    assert candidate["intent_guess"] == "landing"
    deck = extract_candidate(html_evidence(b"<html><title>Product deck slides</title><body>go</body></html>"))
    assert deck["intent_guess"] == "deck"


def test_extract_candidate_rejects_non_html() -> None:
    evidence = html_evidence()
    evidence["content_type"] = "image/png"
    with pytest.raises(IntakeError) as excinfo:
        extract_candidate(evidence)
    assert excinfo.value.code == "intake_not_html"


def test_candidate_store_roundtrip_and_status(tmp_path: Path) -> None:
    store = CandidateStore(tmp_path)
    candidate = extract_candidate(html_evidence(), source={"id": "land-book", "license_class": "reference"})
    store.save(candidate, html_evidence())

    assert [item["candidate_id"] for item in store.list("pending")] == [candidate["candidate_id"]]
    assert store.get(candidate["candidate_id"])["title"] == "Acme Pricing Page"
    assert store.body(candidate["candidate_id"]) == SAMPLE_HTML

    approved = store.set_status(candidate["candidate_id"], "approved")
    assert approved["status"] == "approved"
    assert store.list("pending") == []
    assert len(store.list("approved")) == 1

    with pytest.raises(IntakeError):
        store.set_status(candidate["candidate_id"], "maybe")
    with pytest.raises(IntakeError):
        store.body("../escape")


def test_candidate_store_survives_corrupt_entry(tmp_path: Path) -> None:
    store = CandidateStore(tmp_path)
    candidate = extract_candidate(html_evidence())
    store.save(candidate, html_evidence())
    bad_dir = tmp_path / "intake" / "candidates" / "broken-id"
    bad_dir.mkdir(parents=True)
    (bad_dir / "candidate.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(IntakeError) as excinfo:
        store.list()
    assert excinfo.value.code == "intake_candidate_corrupt"


# ---------------------------------------------------------------- S06 kind extractors

MOTION_SAMPLE = (b"<html><head><title>Motion Lab Inspo</title><style>"
                 b"h1{animation:fade 2s ease-in;transition:all .3s ease}"
                 b"@keyframes fade{from{opacity:0}}</style></head>"
                 b"<body><main><h1>T</h1></main></body></html>")
COMPONENT_SAMPLE = (b"<html><head><title>Component Inspo</title></head><body>"
                    b'<nav class="topnav">links</nav>'
                    b'<section class="hero"><h1>Hero</h1><p>big</p></section>'
                    b'<section class="pricing"><h2>Plans</h2></section></body></html>')


def test_motion_extractor_pulls_patterns(tmp_path: Path) -> None:
    store = CandidateStore(tmp_path)
    source = {"id": "codrops", "kind": "motion", "license_class": "reference"}
    evidence = html_evidence(MOTION_SAMPLE, url="https://example.com/motion")
    candidate = extract_candidate(evidence, source=source)
    assert candidate["kind"] == "motion"
    assert "fade 2s ease-in" in candidate["motion"]["animations"][0]
    assert candidate["motion"]["keyframes"] == ["fade"]
    store.save(candidate, evidence)
    assert store.get(candidate["candidate_id"])["motion"]["animations"]


def test_components_extractor_pulls_sections(tmp_path: Path) -> None:
    store = CandidateStore(tmp_path)
    source = {"id": "comp-src", "kind": "components", "license_class": "reference"}
    candidate = extract_candidate(html_evidence(COMPONENT_SAMPLE, url="https://example.com/comp"),
                                  source=source)
    assert candidate["kind"] == "components"
    tags = [item["tag"] for item in candidate["components"]]
    assert tags == ["nav", "section", "section"]
    hero = candidate["components"][1]
    assert hero["class"] == "hero"
    assert "Hero" in hero["text_head"]
    assert "<h1>" in hero["snippet"]
