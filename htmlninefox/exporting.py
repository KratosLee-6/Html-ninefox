"""Local-first HTML export pipeline for PDF and PNG delivery."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import sys
import uuid
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote

from . import pipeline
from .server.storage import ProjectStore, StoreError

SUPPORTED_FORMATS = ("pdf", "png")
PAPER_FORMATS = ("A4", "Letter", "A3")
_PAGE_LIMIT = 200
_FREEZE_CSS = """
*, *::before, *::after {
  animation-delay: 0s !important;
  animation-duration: 0s !important;
  animation-iteration-count: 1 !important;
  scroll-behavior: auto !important;
  transition-delay: 0s !important;
  transition-duration: 0s !important;
  caret-color: transparent !important;
}
[data-export-hide], .fox-export-hide { display: none !important; }
"""


class _ArtifactParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._inside_title = False
        self.counts = {"slide": 0, "page": 0, "data_page": 0}
        self.features: set[str] = set()
        self.external_assets = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name.lower(): value or "" for name, value in attrs}
        classes = set(attributes.get("class", "").split())
        if "slide" in classes:
            self.counts["slide"] += 1
        if "page" in classes:
            self.counts["page"] += 1
        if "data-page" in attributes:
            self.counts["data_page"] += 1
        if tag in {"canvas", "video", "audio", "iframe"}:
            self.features.add(tag)
        for key in ("src", "href", "poster"):
            value = attributes.get(key, "")
            if value.startswith(("http://", "https://")):
                self.external_assets += 1
        if tag == "title":
            self._inside_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._inside_title = False

    def handle_data(self, data: str) -> None:
        if self._inside_title and not self.title:
            self.title = data.strip()


def runtime_capabilities() -> dict[str, Any]:
    package_ready = importlib.util.find_spec("playwright") is not None
    browsers = [item[0] for item in _browser_candidates(include_default=False)]
    return {
        "engine": "playwright-chromium",
        "package_ready": package_ready,
        "detected_browsers": browsers,
        "formats": list(SUPPORTED_FORMATS),
        "local_only": True,
        "install_hint": (
            "Playwright 未安装，请执行 pip install playwright；Linux 如无 Chromium，再执行 playwright install chromium。"
            if not package_ready else
            "优先使用 Playwright Chromium；未安装内置浏览器时会自动尝试 Edge、Chrome 或系统 Chromium。"
        ),
    }


def analyze_project(root: str | Path, project_name: str) -> dict[str, Any]:
    project, meta, html_path, html_text = _load_project(root, project_name)
    parser = _ArtifactParser()
    parser.feed(html_text)
    lowered = html_text.lower()
    if "webgl" in lowered:
        parser.features.add("webgl")
    if "animation:" in lowered or "@keyframes" in lowered:
        parser.features.add("animation")
    if "filter:" in lowered or "backdrop-filter" in lowered:
        parser.features.add("filter")

    selector, page_count = _page_model(parser, meta.get("intent", ""))
    warnings: list[dict[str, str]] = []
    if parser.external_assets:
        warnings.append(_warning(
            "external_assets", "warning",
            f"检测到 {parser.external_assets} 个网络资源；离线导出时可能缺图或字体。",
        ))
    if parser.features.intersection({"video", "audio", "webgl", "animation"}):
        warnings.append(_warning(
            "dynamic_content_flattened", "info",
            "动画、音视频或 WebGL 会在导出时冻结为静态画面。",
        ))
    if page_count > _PAGE_LIMIT:
        warnings.append(_warning(
            "page_limit", "error", f"检测到 {page_count} 页，当前单次最多导出 {_PAGE_LIMIT} 页。",
        ))
    score = max(45, 100 - sum(20 if item["level"] == "error" else 8 for item in warnings))
    intent = meta.get("intent") or "landing"
    width, height = _default_viewport(intent)
    return {
        "project_name": meta["name"],
        "title": parser.title or meta["name"],
        "intent": intent,
        "preset_id": meta.get("preset_id", ""),
        "source_file": html_path.name,
        "source_size": html_path.stat().st_size,
        "page_model": {"selector": selector, "count": page_count, "paginated": bool(selector)},
        "viewport": {"width": width, "height": height},
        "features": sorted(parser.features),
        "external_assets": parser.external_assets,
        "compatibility_score": score,
        "warnings": warnings,
        "recommended": {
            "format": "pdf" if intent in {"doc", "archdoc", "landing"} else "png",
            "scope": "pages" if selector else "long",
        },
        "runtime": runtime_capabilities(),
        "project_path": str(project),
    }


def normalize_export_request(payload: dict[str, Any]) -> dict[str, Any]:
    project_name = str(payload.get("project_name") or "").strip()
    if not project_name:
        raise StoreError("export_project_required", "请选择需要导出的项目", 400)
    export_format = str(payload.get("format") or "pdf").lower()
    if export_format not in SUPPORTED_FORMATS:
        raise StoreError("export_format_unsupported", "当前版本支持 PDF 和 PNG", 400,
                         {"supported": list(SUPPORTED_FORMATS)})
    scope = str(payload.get("scope") or "auto").lower()
    if scope not in {"auto", "pages", "long"}:
        raise StoreError("export_scope_invalid", "导出范围必须是 auto、pages 或 long", 400)
    width = _bounded_int(payload.get("width"), 320, 3840, 1920, "width")
    height = _bounded_int(payload.get("height"), 240, 2160, 1080, "height")
    scale = _bounded_int(payload.get("scale"), 1, 3, 2, "scale")
    paper = str(payload.get("paper") or "A4")
    if paper not in PAPER_FORMATS:
        raise StoreError("export_paper_invalid", "纸张仅支持 A4、Letter 或 A3", 400)
    pages = _parse_pages(payload.get("pages"))
    return {
        "project_name": project_name,
        "format": export_format,
        "scope": scope,
        "pages": pages,
        "width": width,
        "height": height,
        "scale": scale,
        "paper": paper,
        "landscape": bool(payload.get("landscape", False)),
    }


def export_project(root: str | Path, payload: dict[str, Any]) -> dict[str, Any]:
    request = normalize_export_request(payload)
    manifest = analyze_project(root, request["project_name"])
    if any(item["level"] == "error" for item in manifest["warnings"]):
        raise StoreError("export_analysis_failed", "产物未通过导出分析", 409,
                         {"warnings": manifest["warnings"]})
    project = Path(manifest["project_path"])
    html_path = project / manifest["source_file"]
    export_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    exports_root = project / "exports"
    staging = exports_root / f".{export_id}.tmp"
    target = exports_root / export_id
    staging.mkdir(parents=True, exist_ok=False)
    browser_info: dict[str, Any] = {}
    rendered: list[Path] = []
    export_warnings = list(manifest["warnings"])
    try:
        rendered, browser_info, runtime_warnings = _render(html_path, staging, manifest, request)
        export_warnings.extend(runtime_warnings)
        report = {
            "schema_version": 1,
            "export_id": export_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "source": {
                "project_name": manifest["project_name"],
                "file": manifest["source_file"],
                "intent": manifest["intent"],
                "preset_id": manifest["preset_id"],
            },
            "request": request,
            "manifest": {key: value for key, value in manifest.items() if key != "project_path"},
            "browser": browser_info,
            "warnings": export_warnings,
            "files": [{"name": path.name, "bytes": path.stat().st_size} for path in rendered],
        }
        (staging / "export-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        exports_root.mkdir(parents=True, exist_ok=True)
        os.replace(staging, target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    files = [_file_result(manifest["project_name"], export_id, target / path.name) for path in rendered]
    report_file = target / "export-report.json"
    return {
        "project_name": manifest["project_name"],
        "export_id": export_id,
        "format": request["format"],
        "files": files,
        "report": _file_result(manifest["project_name"], export_id, report_file),
        "warnings": export_warnings,
        "compatibility_score": manifest["compatibility_score"],
        "browser": browser_info,
    }


def _render(html_path: Path, output_dir: Path, manifest: dict[str, Any],
            request: dict[str, Any]) -> tuple[list[Path], dict[str, Any], list[dict[str, str]]]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise StoreError(
            "export_runtime_missing", "缺少 Playwright 导出引擎",
            503, {"hint": "pip install playwright && playwright install chromium"},
        ) from exc

    warnings: list[dict[str, str]] = []
    with sync_playwright() as playwright:
        browser, browser_label = _launch_browser(playwright)
        try:
            context = browser.new_context(
                viewport={"width": request["width"], "height": request["height"]},
                device_scale_factor=request["scale"] if request["format"] == "png" else 1,
            )
            page = context.new_page()
            page.goto(html_path.as_uri(), wait_until="load", timeout=30_000)
            try:
                page.wait_for_load_state("networkidle", timeout=4_000)
            except Exception:  # noqa: BLE001
                warnings.append(_warning(
                    "network_idle_timeout", "info", "页面仍有持续网络请求，已按当前稳定画面导出。"
                ))
            page.add_style_tag(content=_FREEZE_CSS)
            page.wait_for_timeout(250)
            dom_model = _dom_page_model(page, manifest["intent"])
            selector = dom_model["selector"] or manifest["page_model"]["selector"]
            page_count = dom_model["count"] or manifest["page_model"]["count"]
            selected = _selected_pages(request["pages"], page_count)
            scope = request["scope"]
            if scope == "auto":
                scope = "pages" if selector else "long"
            if scope == "pages" and not selector:
                warnings.append(_warning(
                    "page_model_missing", "info", "未检测到分页结构，已改为整页长图或自然分页。"
                ))
                scope = "long"

            if request["format"] == "png":
                files = _render_png(page, output_dir, selector, selected, scope)
            else:
                files = _render_pdf(page, output_dir, selector, selected, scope, request)
            browser_info = {
                "engine": "chromium",
                "source": browser_label,
                "version": browser.version,
                "page_selector": selector,
                "page_count": page_count,
            }
            context.close()
            return files, browser_info, warnings
        finally:
            browser.close()


def _render_png(page, output_dir: Path, selector: str | None, pages: list[int], scope: str) -> list[Path]:
    if scope == "pages" and selector:
        files = []
        for page_number in pages:
            _activate_page(page, selector, page_number - 1)
            target = output_dir / f"page-{page_number:02d}.png"
            page.screenshot(path=str(target), type="png", full_page=False, animations="disabled")
            files.append(target)
        return files
    target = output_dir / "full-page.png"
    page.screenshot(path=str(target), type="png", full_page=True, animations="disabled")
    return [target]


def _render_pdf(page, output_dir: Path, selector: str | None, pages: list[int], scope: str,
                request: dict[str, Any]) -> list[Path]:
    target = output_dir / "document.pdf"
    page.emulate_media(media="print")
    if scope == "pages" and selector:
        page.evaluate(
            """({selector, selected}) => {
                const keep = new Set(selected.map(value => value - 1));
                document.querySelectorAll(selector).forEach((element, index) => {
                    element.toggleAttribute('data-fox-export-skip', !keep.has(index));
                    if (keep.has(index)) element.classList.add('on');
                });
            }""",
            {"selector": selector, "selected": pages},
        )
        page.add_style_tag(content=f"""
            @page {{ size: {request['width']}px {request['height']}px; margin: 0; }}
            html, body {{ margin:0 !important; width:{request['width']}px !important;
              height:auto !important; overflow:visible !important; }}
            .deck, .slides {{ height:auto !important; overflow:visible !important; }}
            {selector} {{ display:flex !important; position:relative !important; inset:auto !important;
              width:{request['width']}px !important; height:{request['height']}px !important;
              min-width:{request['width']}px !important; min-height:{request['height']}px !important;
              opacity:1 !important; visibility:visible !important; transform:none !important;
              overflow:hidden !important; break-after:page !important; page-break-after:always !important; }}
            {selector}[data-fox-export-skip] {{ display:none !important; }}
            .hud, .deck > .nav, .counter {{ display:none !important; }}
        """)
        page.pdf(
            path=str(target), width=f"{request['width']}px", height=f"{request['height']}px",
            print_background=True, prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
    else:
        page.pdf(
            path=str(target), format=request["paper"], landscape=request["landscape"],
            print_background=True, prefer_css_page_size=False,
            margin={"top": "0.35in", "right": "0.35in", "bottom": "0.35in", "left": "0.35in"},
        )
    return [target]


def _activate_page(page, selector: str, index: int) -> None:
    page.evaluate(
        """({selector, index}) => {
            const elements = Array.from(document.querySelectorAll(selector));
            elements.forEach((element, current) => {
                const active = current === index;
                element.classList.toggle('on', active);
                if (active) {
                    element.style.removeProperty('display');
                    element.style.setProperty('opacity', '1', 'important');
                    element.style.setProperty('visibility', 'visible', 'important');
                    element.style.setProperty('transform', 'none', 'important');
                } else {
                    element.style.setProperty('display', 'none', 'important');
                }
            });
            document.querySelectorAll('.hud, .deck > .nav, .counter').forEach(element => {
                element.style.setProperty('display', 'none', 'important');
            });
            document.documentElement.style.setProperty('overflow', 'hidden', 'important');
            document.body.style.setProperty('overflow', 'hidden', 'important');
            window.scrollTo(0, 0);
        }""",
        {"selector": selector, "index": index},
    )
    page.wait_for_timeout(80)


def _dom_page_model(page, intent: str) -> dict[str, Any]:
    return page.evaluate(
        """intent => {
            const candidates = ['.slide', '[data-page]', '.page'];
            const rows = candidates.map(selector => ({selector, count: document.querySelectorAll(selector).length}));
            const preferred = rows.find(row => row.count > 1) ||
                (intent === 'deck' ? rows.find(row => row.count === 1) : null);
            return preferred || {selector: null, count: 1};
        }""",
        intent,
    )


def _launch_browser(playwright):
    attempts: list[dict[str, str]] = []
    for label, options in _browser_candidates(include_default=True):
        try:
            return playwright.chromium.launch(headless=True, args=["--allow-file-access-from-files"], **options), label
        except Exception as exc:  # noqa: BLE001
            attempts.append({"browser": label, "error": str(exc).splitlines()[0][:240]})
    raise StoreError(
        "export_browser_unavailable",
        "没有可用的 Chromium、Edge 或 Chrome，无法导出。",
        503,
        {"attempts": attempts, "hint": "安装 Edge/Chrome，或执行 playwright install chromium。"},
    )


def _browser_candidates(include_default: bool) -> list[tuple[str, dict[str, str]]]:
    rows: list[tuple[str, dict[str, str]]] = []
    if include_default:
        rows.append(("playwright-chromium", {}))
    configured = os.getenv("HTMLNINEFOX_BROWSER_PATH", "").strip()
    if configured and Path(configured).is_file():
        rows.append(("HTMLNINEFOX_BROWSER_PATH", {"executable_path": configured}))
    if sys.platform == "win32":
        rows.extend((channel, {"channel": channel}) for channel in ("msedge", "chrome"))
    elif sys.platform == "darwin":
        rows.extend((channel, {"channel": channel}) for channel in ("chrome", "msedge"))
    else:
        rows.extend((channel, {"channel": channel}) for channel in ("chrome", "msedge"))
    executables = [
        shutil.which(name) for name in
        ("msedge", "microsoft-edge", "google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
    ]
    if sys.platform == "win32":
        for base in (os.getenv("PROGRAMFILES"), os.getenv("PROGRAMFILES(X86)"), os.getenv("LOCALAPPDATA")):
            if base:
                executables.extend([
                    str(Path(base) / "Microsoft/Edge/Application/msedge.exe"),
                    str(Path(base) / "Google/Chrome/Application/chrome.exe"),
                ])
    elif sys.platform == "darwin":
        executables.extend([
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ])
    seen: set[str] = set()
    for executable in executables:
        if not executable:
            continue
        path = str(Path(executable).expanduser())
        if path in seen or not Path(path).is_file():
            continue
        seen.add(path)
        rows.append((Path(path).name, {"executable_path": path}))
    return rows


def _load_project(root: str | Path, project_name: str) -> tuple[Path, dict[str, Any], Path, str]:
    meta = ProjectStore(root).get_project(project_name)
    project = Path(meta["project"])
    html_path = project / "output.html"
    if not html_path.is_file():
        raise StoreError("export_source_missing", "项目缺少 output.html", 409)
    try:
        html_text = html_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise StoreError("export_source_invalid", "HTML 产物无法读取", 409) from exc
    return project, meta, html_path, html_text


def _page_model(parser: _ArtifactParser, intent: str) -> tuple[str | None, int]:
    candidates = [
        (".slide", parser.counts["slide"]),
        ("[data-page]", parser.counts["data_page"]),
        (".page", parser.counts["page"]),
    ]
    for selector, count in candidates:
        if count > 1:
            return selector, count
    if intent == "deck":
        for selector, count in candidates:
            if count == 1:
                return selector, count
    return None, 1


def _selected_pages(requested: list[int], count: int) -> list[int]:
    if count > _PAGE_LIMIT:
        raise StoreError("export_page_limit", f"单次最多导出 {_PAGE_LIMIT} 页", 413)
    if not requested:
        return list(range(1, count + 1))
    invalid = [page for page in requested if page < 1 or page > count]
    if invalid:
        raise StoreError("export_page_out_of_range", "页面范围超出产物页数", 400,
                         {"page_count": count, "invalid": invalid})
    return requested


def _parse_pages(value: Any) -> list[int]:
    if value in (None, "", []):
        return []
    if isinstance(value, list):
        raw = value
    elif isinstance(value, str):
        raw = []
        for part in value.replace("，", ",").split(","):
            item = part.strip()
            if not item:
                continue
            if "-" in item:
                start_text, end_text = item.split("-", 1)
                try:
                    start, end = int(start_text), int(end_text)
                except ValueError as exc:
                    raise StoreError("export_pages_invalid", "页码格式示例：1-3,5", 400) from exc
                if end < start or end - start > _PAGE_LIMIT:
                    raise StoreError("export_pages_invalid", "页码范围无效或过大", 400)
                raw.extend(range(start, end + 1))
            else:
                raw.append(item)
    else:
        raise StoreError("export_pages_invalid", "pages 必须是数组或页码字符串", 400)
    try:
        pages = sorted({int(item) for item in raw})
    except (TypeError, ValueError) as exc:
        raise StoreError("export_pages_invalid", "页码必须是整数", 400) from exc
    if len(pages) > _PAGE_LIMIT:
        raise StoreError("export_page_limit", f"单次最多导出 {_PAGE_LIMIT} 页", 413)
    return pages


def _bounded_int(value: Any, minimum: int, maximum: int, default: int, field: str) -> int:
    if value in (None, ""):
        return default
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise StoreError(f"export_{field}_invalid", f"{field} 必须是整数", 400) from exc
    if number < minimum or number > maximum:
        raise StoreError(f"export_{field}_invalid", f"{field} 必须在 {minimum}-{maximum} 之间", 400)
    return number


def _default_viewport(intent: str) -> tuple[int, int]:
    if intent == "poster":
        return 1080, 1440
    if intent == "deck":
        return 1920, 1080
    return 1440, 900


def _warning(code: str, level: str, message: str) -> dict[str, str]:
    return {"code": code, "level": level, "message": message}


def _file_result(project_name: str, export_id: str, path: Path) -> dict[str, Any]:
    relative = "/".join(quote(item, safe="") for item in (project_name, "exports", export_id, path.name))
    return {
        "name": path.name,
        "bytes": path.stat().st_size,
        "download_url": f"/output/{relative}?download=1",
        "preview_url": f"/output/{relative}",
    }
