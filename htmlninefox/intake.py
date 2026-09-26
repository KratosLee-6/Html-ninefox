"""Design intake: safe reference fetching for the v0.6 intake pipeline.

Every outbound request goes through `validate_url`, which allows only
http/https, resolves the host, and rejects any non-global address
(loopback, private, reserved, link-local, multicast). Redirects are
followed hop by hop with the same validation, and the host is
re-resolved after the response arrives so DNS rebinding cannot swap in
a private target mid-flight.
"""

from __future__ import annotations

import hashlib
import html.parser
import ipaddress
import json
import re
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Callable

import yaml

DATA_SOURCES = Path(__file__).resolve().parent / "data" / "sources"
USER_SOURCES_SUBDIR = "sources"
ALLOWED_SCHEMES = ("http", "https")
LICENSE_CLASSES = ("open", "reference", "inspiration-only")
SOURCE_KINDS = ("gallery", "components", "motion", "typography")
REDIRECT_STATUSES = (301, 302, 303, 307, 308)
DEFAULT_MAX_BYTES = 8 * 1024 * 1024
DEFAULT_TIMEOUT = 20.0
USER_AGENT = "HtmlNineFox-Intake/0.6 (+https://github.com/KratosLee-6/Html-ninefox)"


class IntakeError(ValueError):
    """Stable intake failure: code / message / status."""

    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


# ---------------------------------------------------------------- sources


def _slug(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,40}", value or ""):
        raise IntakeError("intake_source_invalid", f"源 id 非法：{value!r}")
    return value


def _normalize_source(item: object, origin: str) -> dict:
    if not isinstance(item, dict):
        raise IntakeError("intake_source_invalid", f"{origin}: 源必须是对象")
    missing = [key for key in ("id", "kind", "license_class", "entry_url") if not item.get(key)]
    if missing:
        raise IntakeError("intake_source_invalid", f"{origin}: 缺少字段 {missing}")
    source = {
        "id": _slug(str(item["id"])),
        "name": str(item.get("name") or item["id"]),
        "kind": str(item["kind"]),
        "license_class": str(item["license_class"]),
        "entry_url": str(item["entry_url"]),
        "notes": str(item.get("notes") or ""),
        "rate_limit": dict(item.get("rate_limit") or {}),
        "origin": origin,
    }
    if source["kind"] not in SOURCE_KINDS:
        raise IntakeError("intake_source_invalid", f"{origin}: kind 必须是 {SOURCE_KINDS}")
    if source["license_class"] not in LICENSE_CLASSES:
        raise IntakeError("intake_source_invalid", f"{origin}: license_class 必须是 {LICENSE_CLASSES}")
    if urllib.parse.urlsplit(source["entry_url"]).scheme not in ALLOWED_SCHEMES:
        raise IntakeError("intake_source_invalid", f"{origin}: entry_url 仅允许 http/https")
    return source


def load_sources(*, extra_dir: Path | None = None) -> list[dict]:
    """Load built-in + user source registry; same id means user override."""
    sources: dict[str, dict] = {}
    extra = [extra_dir.glob("*.yaml")] if extra_dir else []
    for path in [*DATA_SOURCES.glob("*.yaml"), *(sorted(extra[0]) if extra else [])]:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        items = raw.get("sources") if isinstance(raw, dict) and isinstance(raw.get("sources"), list) else [raw]
        for item in items:
            source = _normalize_source(item, path.name)
            sources[source["id"]] = source
    return sorted(sources.values(), key=lambda s: s["id"])


def find_source(source_id: str, *, extra_dir: Path | None = None) -> dict | None:
    for source in load_sources(extra_dir=extra_dir):
        if source["id"] == source_id:
            return source
    return None


# ---------------------------------------------------------------- safe URL gate


def _is_forbidden_address(ip_text: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_text)
    except ValueError:
        return True
    return (not addr.is_global) or addr.is_multicast or addr.is_unspecified


def _resolve(host: str, resolver: Callable) -> list[str]:
    try:
        ipaddress.ip_address(host)
        return [host]
    except ValueError:
        pass
    try:
        infos = resolver(host, 443)
    except OSError as exc:
        raise IntakeError("intake_host_unresolved", f"无法解析主机：{host}") from exc
    return sorted({info[4][0] for info in infos})


def validate_url(url: str, resolver: Callable | None = None) -> tuple[str, str, list[str]]:
    """Reject everything that is not a public http(s) URL; return scheme/host/ips."""
    resolver = resolver or socket.getaddrinfo
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise IntakeError("intake_scheme_invalid", "仅允许 http/https 地址")
    host = parsed.hostname
    if not host:
        raise IntakeError("intake_url_invalid", "地址缺少主机名")
    ips = _resolve(host, resolver)
    for ip_text in ips:
        if _is_forbidden_address(ip_text):
            raise IntakeError("intake_host_forbidden", f"拒绝非公网地址：{host}", 403)
    return parsed.scheme, host, ips


# ---------------------------------------------------------------- transport


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _default_transport(url: str, headers: dict[str, str], timeout: float, max_bytes: int):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers})
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=timeout) as response:
            status = response.status
            resp_headers = {key.lower(): value for key, value in response.headers.items()}
            body = response.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        if exc.code in REDIRECT_STATUSES:
            return exc.code, {key.lower(): value for key, value in exc.headers.items()}, b""
        raise IntakeError("intake_fetch_failed", f"远端返回 HTTP {exc.code}", 502) from exc
    except (urllib.error.URLError, OSError) as exc:
        raise IntakeError("intake_fetch_failed", f"连接失败：{exc}") from exc
    if len(body) > max_bytes:
        raise IntakeError("intake_too_large", f"响应超过 {max_bytes} 字节上限", 413)
    return status, resp_headers, body


# ---------------------------------------------------------------- fetching


def fetch_reference(
    url: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    timeout: float = DEFAULT_TIMEOUT,
    max_hops: int = 3,
    headers: dict[str, str] | None = None,
    transport: Callable | None = None,
    resolver: Callable | None = None,
) -> dict:
    """Fetch a public reference page safely; returns evidence, never auto-follows blindly."""
    transport = transport or _default_transport
    current_url = url
    followed: list[str] = [url]
    for _ in range(max_hops + 1):
        _, host, before_ips = validate_url(current_url, resolver)
        status, resp_headers, body = transport(current_url, headers or {}, timeout, max_bytes)
        if status in REDIRECT_STATUSES:
            location = resp_headers.get("location", "")
            if not location:
                raise IntakeError("intake_fetch_failed", "重定向缺少 Location", 502)
            current_url = urllib.parse.urljoin(current_url, location)
            followed.append(current_url)
            continue
        if len(body) > max_bytes:
            raise IntakeError("intake_too_large", f"响应超过 {max_bytes} 字节上限", 413)
        # Post-fetch rebinding check: if the host now resolves somewhere new,
        # the bytes cannot be trusted and are discarded.
        after_ips = _resolve(host, resolver)
        if set(after_ips) != set(before_ips):
            raise IntakeError("intake_rebind_suspected", "主机解析在请求期间变化，响应已丢弃", 502)
        if status != 200:
            raise IntakeError("intake_fetch_failed", f"远端返回 HTTP {status}", 502)
        return {
            "url": url,
            "final_url": current_url,
            "followed": followed,
            "status": status,
            "content_type": resp_headers.get("content-type", ""),
            "body": body,
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "body_bytes": len(body),
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
        }
    raise IntakeError("intake_too_many_redirects", f"重定向超过 {max_hops} 跳", 502)


# ---------------------------------------------------------------- evidence store


def _slugify_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    tail = re.sub(r"[^a-z0-9-]+", "-", (parsed.path or "/").strip("/").lower()).strip("-")
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    return f"{parsed.hostname or 'page'}-{tail[:48] or 'root'}-{digest}"


def save_evidence(root: Path, source_id: str, evidence: dict) -> Path:
    """Persist fetch evidence under <root>/intake/<source>/<slug>/."""
    target = Path(root) / "intake" / _slug(source_id) / _slugify_url(evidence["final_url"])
    target.mkdir(parents=True, exist_ok=True)
    content_type = evidence.get("content_type", "")
    extension = ".html" if "html" in content_type else ".css" if "css" in content_type else ".bin"
    (target / f"body{extension}").write_bytes(evidence["body"])
    meta = {key: value for key, value in evidence.items() if key != "body"}
    (target / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return target


# ---------------------------------------------------------------- rate limiting


class RateLimiter:
    """Per-key minimum interval between fetches; injectable clock and sleep."""

    def __init__(self, default_interval: float = 6.0,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        self.default_interval = default_interval
        self._clock = clock
        self._sleep = sleep
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, key: str, interval: float | None = None) -> float:
        """Reserve the next slot for key; returns and honours the delay."""
        interval = self.default_interval if interval is None else interval
        with self._lock:
            reserved = max(self._clock(), self._last.get(key, float("-inf")) + interval)
            self._last[key] = reserved
            delay = max(0.0, reserved - self._clock())
        if delay > 0:
            self._sleep(delay)
        return delay


# ---------------------------------------------------------------- candidate extraction

INTENT_KEYWORDS = {
    "deck": ("slide", "deck", "ppt", "演示", "发布会", "幻灯"),
    "dashboard": ("dashboard", "metric", "analytics", "看板", "数据"),
    "poster": ("poster", "海报"),
    "archdoc": ("architecture", "archdoc", "架构"),
    "doc": ("documentation", "whitepaper", "文档", "白皮书"),
}

COLOR_PATTERN = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]+\)|hsla?\([^)]+\)")
FONT_PATTERN = re.compile(r"font-family\s*:\s*([^;}]+)", re.IGNORECASE)
SECTION_TAGS = ("nav", "header", "main", "section", "article", "aside", "footer")


class _SkeletonParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._in_title = False
        self.headings: list[dict[str, str]] = []
        self._heading_level: int | None = None
        self._heading_text: list[str] = []
        self.semantic: dict[str, int] = {}
        self.links = 0
        self.images = 0

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading_level = int(tag[1])
            self._heading_text = []
        elif tag in SECTION_TAGS:
            self.semantic[tag] = self.semantic.get(tag, 0) + 1
        elif tag == "a":
            self.links += 1
        elif tag == "img":
            self.images += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._heading_level is not None:
            text = " ".join("".join(self._heading_text).split())[:120]
            if text:
                self.headings.append({"level": self._heading_level, "text": text})
            self._heading_level = None
            self._heading_text = []

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._heading_level is not None:
            self._heading_text.append(data)


def _guess_intent(title: str, headings: list[dict[str, str]]) -> str:
    corpus = (title + " " + " ".join(item["text"] for item in headings)).lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in corpus for keyword in keywords):
            return intent
    return "landing"


def extract_candidate(evidence: dict, *, source: dict | None = None,
                      notes: str = "") -> dict:
    """Turn fetch evidence into a pending review candidate (skeleton + tokens)."""
    content_type = evidence.get("content_type", "")
    if "html" not in content_type:
        raise IntakeError("intake_not_html", "抓取内容不是 HTML 页面", 415)
    html_text = evidence["body"].decode("utf-8", errors="replace")
    parser = _SkeletonParser()
    try:
        parser.feed(html_text)
    except Exception:  # noqa: BLE001 - 畸形页面也要能出候选
        pass
    style_blob = " ".join(re.findall(r"<style[^>]*>(.*?)</style>", html_text, re.S | re.I))
    style_blob += " " + " ".join(re.findall(r'style="([^"]+)"', html_text))
    colors: list[str] = []
    for match in COLOR_PATTERN.findall(style_blob):
        value = match.strip()
        if value not in colors:
            colors.append(value)
    fonts: list[str] = []
    for match in FONT_PATTERN.findall(style_blob):
        name = match.split(",")[0].strip().strip("'\"")
        if name and name not in fonts and not name.startswith("-"):
            fonts.append(name)
    candidate = {
        "candidate_id": _slugify_url(evidence["final_url"]),
        "url": evidence["url"],
        "final_url": evidence["final_url"],
        "source": source["id"] if source else "",
        "license_class": source["license_class"] if source else "reference",
        "title": parser.title.strip()[:120] or evidence["final_url"],
        "intent_guess": _guess_intent(parser.title, parser.headings),
        "tokens": {"colors": colors[:24], "fonts": fonts[:8]},
        "skeleton": {
            "headings": parser.headings[:24],
            "semantic": parser.semantic,
            "links": parser.links,
            "images": parser.images,
        },
        "notes": notes,
        "status": "pending",
        "fetched_at": evidence["fetched_at"],
        "body_sha256": evidence["body_sha256"],
    }
    return candidate


class CandidateStore:
    """Pending review candidates under <root>/intake/candidates/<id>/."""

    def __init__(self, root: str | Path):
        self.root = Path(root) / "intake"

    def _dir(self, candidate_id: str) -> Path:
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,120}", candidate_id or ""):
            raise IntakeError("intake_candidate_invalid", f"候选 id 非法：{candidate_id!r}")
        return self.root / "candidates" / candidate_id

    def save(self, candidate: dict, evidence: dict) -> dict:
        target = self._dir(candidate["candidate_id"])
        target.mkdir(parents=True, exist_ok=True)
        (target / "candidate.json").write_text(
            json.dumps(candidate, ensure_ascii=False, indent=2), encoding="utf-8")
        (target / "body.html").write_bytes(evidence["body"])
        return candidate

    def _read(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise IntakeError("intake_candidate_corrupt", "候选素材数据损坏", 409) from exc

    def list(self, status: str | None = None) -> list[dict]:
        items: list[dict] = []
        directory = self.root / "candidates"
        if not directory.is_dir():
            return items
        for path in directory.glob("*/candidate.json"):
            candidate = self._read(path)
            if status is None or candidate.get("status") == status:
                items.append(candidate)
        return sorted(items, key=lambda item: item.get("fetched_at", ""), reverse=True)

    def get(self, candidate_id: str) -> dict:
        return self._read(self._dir(candidate_id) / "candidate.json")

    def body(self, candidate_id: str) -> bytes:
        path = self._dir(candidate_id) / "body.html"
        if not path.is_file():
            raise IntakeError("intake_candidate_missing", "候选缺少抓取正文", 404)
        return path.read_bytes()

    def set_status(self, candidate_id: str, status: str) -> dict:
        if status not in {"pending", "approved", "rejected"}:
            raise IntakeError("intake_status_invalid", "状态只允许 pending/approved/rejected")
        candidate = self.get(candidate_id)
        candidate["status"] = status
        (self._dir(candidate_id) / "candidate.json").write_text(
            json.dumps(candidate, ensure_ascii=False, indent=2), encoding="utf-8")
        return candidate
