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
    # hostname must be normalized too (unicode/underscore hosts would fail
    # the store-side id validation and break the whole import)
    host = re.sub(r"[^a-z0-9-]+", "-", (parsed.hostname or "page").lower()).strip("-") or "page"
    tail = re.sub(r"[^a-z0-9-]+", "-", (parsed.path or "/").strip("/").lower()).strip("-")
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    return f"{host[:48]}-{tail[:48] or 'root'}-{digest}"


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
def _normalize_color(value: str) -> str | None:
    """Reduce a css color to a safe #RRGGBB token (kills css-injection via style attrs)."""
    value = value.strip()
    if value.startswith("#"):
        hex_part = value[1:]
        if len(hex_part) == 3:
            return "#" + "".join(ch * 2 for ch in hex_part).upper()
        if len(hex_part) in (6, 8):
            return "#" + hex_part[:6].upper()
        return None
    digits = re.findall(r"\d+", value)
    if len(digits) >= 3:
        try:
            r, g, b = (max(0, min(255, int(part))) for part in digits[:3])
        except ValueError:
            return None
        return f"#{r:02X}{g:02X}{b:02X}"
    return None


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
        value = _normalize_color(match)
        if value and value not in colors:
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
        "kind": (source.get("kind") if source else "gallery") or "gallery",
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
    extractor = KIND_EXTRACTORS.get(candidate["kind"])
    if extractor is not None:
        candidate.update(extractor(evidence, html_text, style_blob))
    if candidate["license_class"] == "open":
        gradients = list(dict.fromkeys(
            gradient.strip() for gradient in
            re.findall(r"(?:linear|radial)-gradient\([^;{}]+\)", style_blob, re.I)))[:8]
        candidate["decorations"] = gradients
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


# ---------------------------------------------------------------- kind extractors (S06)

MOTION_TRANSITION = re.compile(r"transition\s*:[^;}]+", re.I)
MOTION_ANIMATION = re.compile(r"animation\s*:[^;}]+", re.I)
KEYFRAMES_NAME = re.compile(r"@keyframes\s+([\w-]+)", re.I)
FONT_SIZE = re.compile(r"font-size\s*:\s*([^;}]+)", re.I)
LINE_HEIGHT = re.compile(r"line-height\s*:\s*([^;}]+)", re.I)


def extract_components(evidence: dict, html_text: str, style_blob: str = "") -> dict:
    """Section-level component candidates: each semantic section as a bounded snippet."""
    sections: list[dict] = []
    closing = chr(60) + chr(47) + "\\1" + chr(62)
    pattern = re.compile(
        r"<(" + "|".join(SECTION_TAGS) + r")([^>]*)>(.*?)" + closing, re.S | re.I)
    for match in pattern.finditer(html_text):
        tag, attrs, inner = match.group(1).lower(), match.group(2), match.group(3)
        class_match = re.search(r'class="([^"]*)"', attrs)
        text_head = " ".join(re.sub(r"<[^>]+>", " ", inner).split())[:160]
        sections.append({
            "tag": tag,
            "class": class_match.group(1)[:120] if class_match else "",
            "text_head": text_head,
            "snippet": match.group(0)[:4000],
        })
        if len(sections) >= 12:
            break
    return {"components": sections}


def extract_motion(evidence: dict, html_text: str, style_blob: str) -> dict:
    """Motion patterns: transitions, animation shorthands, keyframes names."""
    transitions = list(dict.fromkeys(line.strip() for line in MOTION_TRANSITION.findall(style_blob)))[:16]
    animations = list(dict.fromkeys(line.strip() for line in MOTION_ANIMATION.findall(style_blob)))[:16]
    keyframes = list(dict.fromkeys(KEYFRAMES_NAME.findall(html_text + " " + style_blob)))[:16]
    return {"motion": {"transitions": transitions, "animations": animations, "keyframes": keyframes}}


def extract_typography(evidence: dict, html_text: str, style_blob: str) -> dict:
    """Typography scale: font stacks, size steps, line heights.

    Signature matches the other KIND_EXTRACTORS entries
    (evidence, html_text, style_blob): the dispatch at extract_candidate()
    calls every extractor with the same three arguments, so a two-parameter
    signature made every typography candidate raise TypeError. Typography
    sources are the only `open` license tier, so that tier was unreachable.
    """
    sizes = list(dict.fromkeys(value.strip() for value in FONT_SIZE.findall(style_blob)))[:16]
    heights = list(dict.fromkeys(value.strip() for value in LINE_HEIGHT.findall(style_blob)))[:12]
    return {"typography": {"sizes": sizes, "line_heights": heights}}


KIND_EXTRACTORS = {"components": extract_components, "motion": extract_motion,
                   "typography": extract_typography}


# ---------------------------------------------------------------- component library (S09)

class ComponentStore:
    """Approved section components under <root>/.library/intake/components/."""

    def __init__(self, root: str | Path):
        self.root = Path(root) / ".library" / "intake" / "components"

    def import_from_candidate(self, candidate: dict) -> list[dict]:
        """Register each extracted section of an approved components-kind candidate."""
        if candidate.get("status") != "approved":
            raise IntakeError("intake_candidate_not_approved", "只有已采纳的候选才能导入组件", 409)
        if candidate.get("kind") != "components":
            raise IntakeError("intake_kind_invalid", "该候选不是组件类来源", 409)
        self.root.mkdir(parents=True, exist_ok=True)
        registered: list[dict] = []
        for index, section in enumerate(candidate.get("components") or []):
            component = {
                "component_id": f"{candidate['candidate_id']}-{index}",
                "candidate_id": candidate["candidate_id"],
                "name": (section.get("class") or f"{section['tag']} 组件")[:60],
                "tag": section.get("tag", "section"),
                "text": section.get("text_head", ""),
                "snippet": section.get("snippet", ""),
                "license_class": candidate.get("license_class", "reference"),
                "source": candidate.get("source", ""),
            }
            path = self.root / f"{component['component_id']}.json"
            path.write_text(json.dumps(component, ensure_ascii=False, indent=2),
                            encoding="utf-8")
            registered.append(component)
        return registered

    def list(self) -> list[dict]:
        if not self.root.is_dir():
            return []
        items = []
        for path in sorted(self.root.glob("*.json")):
            try:
                items.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return items


# ---------------------------------------------------------------- motion styles (S10)

MOTION_BUDGET_MS = (120, 500)
TIME_TOKEN = re.compile(r"(\d*\.?\d+m?s)\b")
EASING_TOKEN = re.compile(r"(cubic-bezier\([^)]*\)|steps\([^)]*\)|ease-in-out|ease-in|ease-out|linear|ease)")


def _clamp_duration(token: str) -> int:
    value = float(token[:-2]) if token.endswith("ms") else float(token[:-1]) * 1000
    return int(max(MOTION_BUDGET_MS[0], min(MOTION_BUDGET_MS[1], value)))


def build_motion_styles(candidate: dict) -> dict:
    """Generate ORIGINAL motion CSS from extracted parameters only.

    Durations are clamped to the motion budget, keyframes are generic
    original implementations, and every rule carries a
    prefers-reduced-motion guard. No reference CSS is copied.
    """
    patterns = candidate.get("motion") or {}
    rules: list[str] = []
    durations: list[str] = []
    easings: list[str] = []
    anim_count = 0
    trans_count = 0
    for index, shorthand in enumerate(patterns.get("animations", [])[:8]):
        timing = TIME_TOKEN.search(shorthand)
        easing = EASING_TOKEN.search(shorthand)
        duration = _clamp_duration(timing.group(1)) if timing else 300
        easing_value = easing.group(1) if easing else "ease"
        durations.append(f"{duration}ms")
        easings.append(easing_value)
        rules.append(
            f"/* 吸收动效 #{index + 1} · 时长 {duration}ms · 缓动 {easing_value}（原创实现） */\n"
            f"@keyframes fox-intake-{anim_count}-in {{\n"
            f"  from {{ opacity: 0; transform: translateY(6px); }}\n"
            f"  to {{ opacity: 1; transform: none; }}\n"
            f"}}\n"
            f".fox-intake-{anim_count} {{ animation: fox-intake-{anim_count}-in "
            f"{duration}ms {easing_value} both; }}")
        anim_count += 1
    for index, shorthand in enumerate(patterns.get("transitions", [])[:8]):
        timing = TIME_TOKEN.search(shorthand)
        easing = EASING_TOKEN.search(shorthand)
        duration = _clamp_duration(timing.group(1)) if timing else 200
        easing_value = easing.group(1) if easing else "ease"
        durations.append(f"{duration}ms")
        easings.append(easing_value)
        rules.append(
            f"/* 吸收过渡 #{index + 1} · 时长 {duration}ms · 缓动 {easing_value} */\n"
            f".fox-intake-t{trans_count} {{ transition: all {duration}ms {easing_value}; }}")
        trans_count += 1
    if rules:
        guards = "\n".join(
            f".fox-intake-{i} {{ animation: none; }}" for i in range(anim_count))
        css = ("\n\n".join(rules)
               + "\n\n@media (prefers-reduced-motion: reduce) {\n"
               + guards + "\n}\n")
    else:
        css = ""
    return {
        "motion_id": _slugify_url(candidate["final_url"]),
        "name": (candidate.get("title") or "Intake Motion")[:60],
        "css": css,
        "patterns": {"durations": durations, "easings": easings},
        "license_class": candidate.get("license_class", "reference"),
        "source": candidate.get("source", ""),
    }


class MotionStore:
    """Original motion style candidates under <root>/.library/intake/motion/."""

    def __init__(self, root: str | Path):
        self.root = Path(root) / ".library" / "intake" / "motion"

    def import_from_candidate(self, candidate: dict) -> dict:
        if candidate.get("status") != "approved":
            raise IntakeError("intake_candidate_not_approved", "只有已采纳的候选才能导入动效", 409)
        if candidate.get("kind") != "motion":
            raise IntakeError("intake_kind_invalid", "该候选不是动效类来源", 409)
        entry = build_motion_styles(candidate)
        if not entry["css"]:
            raise IntakeError("intake_motion_empty", "候选中没有可吸收的动效模式", 422)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / f"{entry['motion_id']}.json").write_text(
            json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
        return entry

    def list(self) -> list[dict]:
        if not self.root.is_dir():
            return []
        items = []
        for path in sorted(self.root.glob("*.json")):
            try:
                items.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return items


# ---------------------------------------------------------------- AI analysis (S11)

ANALYSIS_SYSTEM_PROMPT = (
    "你是网页设计分析专家。基于给定的页面骨架与设计令牌，输出严格的 JSON："
    '{"description": "一句话概括页面设计", "tags": ["3-6个设计标签"], '
    '"layout_notes": "布局系统说明（≤120字）", "content_recipe": "内容配方建议（栏目结构，≤120字）"}'
    " 只输出 JSON，不要其他文字。"
)


def build_analysis_prompt(candidate: dict) -> str:
    headings = "；".join(
        f"h{item['level']}:{item['text']}" for item in (candidate.get("skeleton") or {}).get("headings", []))
    tokens = candidate.get("tokens") or {}
    return (
        f"页面标题：{candidate.get('title', '')}\n"
        f"标题结构：{headings or '无'}\n"
        f"语义区块：{json.dumps((candidate.get('skeleton') or {}).get('semantic', {}), ensure_ascii=False)}\n"
        f"颜色令牌：{json.dumps(tokens.get('colors', []), ensure_ascii=False)}\n"
        f"字体：{json.dumps(tokens.get('fonts', []), ensure_ascii=False)}\n"
        f"来源类型：{candidate.get('kind', 'gallery')}\n"
        "请输出分析 JSON。")


def parse_analysis(text: str) -> dict:
    """Leniently parse the model's JSON (tolerates code fences)."""
    cleaned = re.sub(r"```(?:json)?|```", "", text).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        raise IntakeError("intake_analysis_invalid", "AI 返回内容不是有效 JSON", 502)
    try:
        payload = json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError as exc:
        raise IntakeError("intake_analysis_invalid", "AI 返回内容解析失败", 502) from exc
    return {
        "description": str(payload.get("description") or "")[:300],
        "tags": [str(tag)[:24] for tag in (payload.get("tags") or [])[:6]],
        "layout_notes": str(payload.get("layout_notes") or "")[:200],
        "content_recipe": str(payload.get("content_recipe") or "")[:200],
    }


def apply_analysis(candidate: dict, analysis: dict) -> dict:
    candidate["ai_analysis"] = {**analysis, "analyzed_at": datetime.now().isoformat(timespec="seconds")}
    for tag in analysis.get("tags", []):
        if tag and tag not in candidate.setdefault("ai_tags", []):
            candidate["ai_tags"].append(tag)
    return candidate


# ---------------------------------------------------------------- manual import (S04)

ZIP_MAX_ENTRIES = 24
ZIP_MAX_TOTAL_BYTES = 24 * 1024 * 1024
BATCH_MAX_URLS = 10


def zip_html_entries(data: bytes) -> list[dict]:
    """Extract HTML members from an uploaded ZIP (in memory, bounded).

    Path traversal is impossible by construction: only the basename of
    each member is used and nothing is written to disk here.
    """
    import io
    import zipfile

    if len(data) > ZIP_MAX_TOTAL_BYTES:
        raise IntakeError("intake_too_large", f"ZIP 超过 {ZIP_MAX_TOTAL_BYTES} 字节上限", 413)
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise IntakeError("intake_zip_invalid", "不是有效的 ZIP 文件", 400) from exc
    members: list[dict] = []
    total = 0
    for info in archive.infolist():
        if info.is_dir():
            continue
        if not info.filename.lower().endswith((".html", ".htm")):
            continue
        if total + info.file_size > ZIP_MAX_TOTAL_BYTES:
            raise IntakeError("intake_too_large", "ZIP 解压后超过大小上限", 413)
        body = archive.read(info)
        total += len(body)
        name = Path(info.filename).stem or "page"
        members.append({"name": name[:80], "body": body})
        if len(members) >= ZIP_MAX_ENTRIES:
            break
    if not members:
        raise IntakeError("intake_zip_empty", "ZIP 中没有 HTML 文件", 400)
    return members


def batch_urls(raw_urls: list[str]) -> list[str]:
    """Normalize and bound a user-supplied URL list (dedup, cap count)."""
    urls: list[str] = []
    for raw in raw_urls or []:
        url = str(raw).strip()
        if url and url not in urls:
            urls.append(url)
    if not urls:
        raise IntakeError("intake_url_invalid", "至少需要一个 URL", 400)
    if len(urls) > BATCH_MAX_URLS:
        raise IntakeError("intake_batch_too_many", f"单批最多 {BATCH_MAX_URLS} 个 URL", 400)
    return urls


# ---------------------------------------------------------------- style presets (S08)

STYLE_PRESET_SCHEMA = 1


def _hex_solid(color: str) -> str:
    """Pick a solid hex from a css color string; fallback cobalt."""
    if color.startswith("#"):
        value = color[1:]
        if len(value) in (3, 6):
            return "#" + value
    digits = re.findall(r"\d+", color)
    if len(digits) >= 3:
        r, g, b = (max(0, min(255, int(part))) for part in digits[:3])
        return f"#{r:02X}{g:02X}{b:02X}"
    return "#173C8F"


def build_style_preset(candidate: dict) -> dict:
    """Turn an approved candidate's tokens into a user style preset."""
    colors = [color for color in (candidate.get("tokens") or {}).get("colors", [])
              if color.startswith("#")]
    fonts = (candidate.get("tokens") or {}).get("fonts", [])
    primary = _hex_solid(colors[0]) if colors else "#173C8F"
    accent = _hex_solid(colors[1]) if len(colors) > 1 else "#49B894"
    font_stack = fonts[0] if fonts else "Inter"
    name = (candidate.get("title") or "Intake Style")[:60]
    return {
        "schema": STYLE_PRESET_SCHEMA,
        "preset_id": candidate["candidate_id"],
        "name": name,
        "dark": False,
        "visual_system": "intake",
        "origin": f"设计吸收 · {candidate.get('source') or '手动导入'}",
        "fonts": {"heading": font_stack, "body": font_stack},
        "colors": {"primary": primary, "accent": accent, "bg": "#FFFDF6"},
        "candidate": candidate["candidate_id"],
        "license_class": candidate.get("license_class", "reference"),
    }


class StylePresetStore:
    """Style preset candidates under <root>/.library/intake/style-presets/."""

    def __init__(self, root: str | Path):
        self.root = Path(root) / ".library" / "intake" / "style-presets"

    def _path(self, preset_id: str) -> Path:
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,120}", preset_id or ""):
            raise IntakeError("intake_candidate_invalid", f"预设 id 非法：{preset_id!r}")
        return self.root / f"{preset_id}.json"

    def save(self, preset: dict) -> dict:
        self.root.mkdir(parents=True, exist_ok=True)
        self._path(preset["preset_id"]).write_text(
            json.dumps(preset, ensure_ascii=False, indent=2), encoding="utf-8")
        return preset

    def get(self, preset_id: str) -> dict:
        path = self._path(preset_id)
        if not path.is_file():
            raise IntakeError("intake_preset_missing", "风格预设不存在", 404)
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self) -> list[dict]:
        if not self.root.is_dir():
            return []
        return sorted((json.loads(path.read_text(encoding="utf-8"))
                       for path in self.root.glob("*.json")),
                      key=lambda item: item.get("name", ""))

    def apply(self, preset_id: str, templates_dir: Path) -> Path:
        """Write the preset as a user template (pipeline.list_templates reads it)."""
        preset = self.get(preset_id)
        target = Path(templates_dir) / re.sub(r"[^\w.-]+", "-", preset["name"]).strip("-").lower()[:48]
        target.mkdir(parents=True, exist_ok=True)
        (target / "style.json").write_text(
            json.dumps(preset, ensure_ascii=False, indent=2), encoding="utf-8")
        return target
