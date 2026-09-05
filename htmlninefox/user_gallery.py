"""Private real-HTML gallery packages imported by the local workbench."""

from __future__ import annotations

import base64
import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

MAX_FILES = 120
MAX_TOTAL_BYTES = 24 * 1024 * 1024
ALLOWED_SUFFIXES = {
    ".html", ".htm", ".css", ".js", ".mjs", ".json", ".txt", ".md",
    ".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico",
    ".woff", ".woff2", ".ttf", ".otf", ".mp4", ".webm",
}
HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
HEADING_RE = re.compile(r"<h[1-3][^>]*>(.*?)</h[1-3]>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
DATA_PAGE_RE = re.compile(r"data-page=[\"']([^\"']+)[\"']", re.I)
PAGE_CLASS_RE = re.compile(r"class=[\"'][^\"']*\b(page|slide)\b[^\"']*[\"']", re.I)
FONT_RE = re.compile(r"font-family\s*:\s*([^;}{]+)", re.I)
BLOCKS_BY_INTENT = {
    "deck": ["cover", "problem", "solution", "demo", "metrics", "roadmap", "ending"],
    "dashboard": ["topbar", "kpi_row", "charts", "table", "activity"],
    "doc": ["title", "summary", "sections", "key_points", "table", "conclusion"],
    "landing": ["nav", "hero", "features", "showcase", "pricing", "faq", "cta_footer"],
}
BLOCK_KEYWORDS = {
    "cover": ("封面", "首页", "cover"), "problem": ("问题", "现状", "痛点", "why"),
    "solution": ("方案", "架构", "解法", "路径", "solution"), "demo": ("演示", "案例", "模块", "demo"),
    "metrics": ("数据", "结果", "价格", "报价", "成本", "账", "metric"),
    "roadmap": ("路线", "计划", "阶段", "时间", "实施", "roadmap"),
    "ending": ("结尾", "总结", "行动", "ending"), "topbar": ("封面", "总览", "首页"),
    "kpi_row": ("指标", "概览", "统计", "kpi"), "charts": ("趋势", "图表", "分析", "chart"),
    "table": ("表", "清单", "列表", "管理", "订单", "数据"), "activity": ("日志", "动态", "记录"),
    "title": ("标题", "封面", "首页"), "summary": ("摘要", "结论", "概述"),
    "sections": ("章节", "分析", "背景"), "key_points": ("要点", "发现", "洞察"),
    "conclusion": ("结论", "建议", "总结"), "nav": ("导航",), "hero": ("首页", "封面", "hero"),
    "features": ("功能", "能力", "特性"), "showcase": ("案例", "展示", "作品"),
    "pricing": ("价格", "报价", "套餐"), "faq": ("问题", "faq"), "cta_footer": ("行动", "联系", "开始"),
}


class UserGalleryError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub("", value)).strip()


def _safe_relpath(raw: str) -> PurePosixPath:
    value = str(raw or "").replace("\\", "/").strip("/")
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or ":" in path.parts[0]:
        raise UserGalleryError(f"不安全的模板文件路径：{raw}")
    if any(part in {"", "."} for part in path.parts):
        raise UserGalleryError(f"无效的模板文件路径：{raw}")
    return path


def _slug(value: str) -> str:
    result = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value).strip("-")[:48]
    return result or "html-template"


def _package_id(value: str) -> str:
    package_id = _slug(value)
    if not package_id.startswith("user-"):
        raise UserGalleryError(f"私人模板 ID 无效：{value}")
    return package_id


def _title(html: str, fallback: str) -> str:
    match = TITLE_RE.search(html)
    return _clean_text(match.group(1))[:80] if match else fallback


def _intent(title: str, html: str, html_count: int) -> str:
    text = f"{title} {html[:12000]}".lower()
    if html_count > 1 or any(word in text for word in ("后台", "admin", "prototype", "原型")):
        return "dashboard"
    if any(word in text for word in ("slide", "data-page", "ppt", "演示", "发布会")):
        return "deck"
    if any(word in text for word in ("报告", "调研", "research", "report")):
        return "doc"
    return "landing"


def _block_id(name: str, intent: str, index: int) -> str:
    lowered = name.lower()
    for block_id in BLOCKS_BY_INTENT[intent]:
        if any(keyword in lowered for keyword in BLOCK_KEYWORDS.get(block_id, ())):
            return block_id
    blocks = BLOCKS_BY_INTENT[intent]
    return blocks[min(index, len(blocks) - 1)]


def _style_overrides(colors: list[str], fonts: list[str]) -> dict[str, str]:
    primary = next((color for color in colors if color not in {"#FFFFFF", "#000000"}
                    and not all(int(color[index:index + 2], 16) > 235 for index in (1, 3, 5))
                    and not all(int(color[index:index + 2], 16) < 24 for index in (1, 3, 5))), "")
    font_text = " ".join(fonts).lower()
    font = "serif" if any(value in font_text for value in ("serif", "songti", "simsun")) else (
        "mono" if any(value in font_text for value in ("mono", "consolas")) else "sans")
    return {key: value for key, value in {"primary": primary, "font": font}.items() if value}


def _single_file_pages(html: str, entry: str) -> list[dict[str, Any]]:
    page_ids = list(dict.fromkeys(DATA_PAGE_RE.findall(html)))
    headings = [_clean_text(value)[:40] for value in HEADING_RE.findall(html)]
    if page_ids:
        pages = [{"id": _slug(page_id), "name": headings[index] if index < len(headings) else page_id, "file": entry,
                 "selector": "[data-page]", "index": index,
                 } for index, page_id in enumerate(page_ids[:40])]
        return pages
    count = len(PAGE_CLASS_RE.findall(html))
    if count > 1:
        return [{"id": f"page-{index + 1}",
                 "name": headings[index] if index < len(headings) else f"页面 {index + 1}", "file": entry,
                 "selector": ".page, .slide", "index": index}
                for index in range(min(count, 40))]
    heading = HEADING_RE.search(html)
    return [{"id": "full", "name": _clean_text(heading.group(1))[:40] if heading else "完整页面",
             "file": entry}]


def _manifest(root: Path, package_id: str) -> dict[str, Any]:
    safe_id = _package_id(package_id)
    path = root / safe_id / "manifest.json"
    if not path.is_file():
        raise UserGalleryError(f"私人模板不存在：{safe_id}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("id") != safe_id or manifest.get("source") != "user":
        raise UserGalleryError(f"私人模板清单无效：{safe_id}")
    return manifest


class UserGalleryStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[dict[str, Any]]:
        items = []
        for directory in sorted(self.root.iterdir()):
            if not directory.is_dir() or directory.name.startswith(".import-"):
                continue
            try:
                items.append(_manifest(self.root, directory.name))
            except (OSError, json.JSONDecodeError, UserGalleryError):
                continue
        return items

    def get(self, package_id: str) -> dict[str, Any]:
        return _manifest(self.root, package_id)

    def import_files(self, files: list[dict[str, Any]], name: str = "",
                     entry: str = "", tags: list[str] | None = None) -> dict[str, Any]:
        if not files or len(files) > MAX_FILES:
            raise UserGalleryError(f"模板包文件数量需为 1–{MAX_FILES} 个")
        staging = self.root / f".import-{uuid.uuid4().hex}"
        staging.mkdir(parents=True)
        html_paths: list[PurePosixPath] = []
        token_sources: list[str] = []
        total = 0
        copied = 0
        ignored = 0
        try:
            for item in files:
                rel = _safe_relpath(str(item.get("path") or item.get("name") or ""))
                if rel.suffix.lower() not in ALLOWED_SUFFIXES:
                    ignored += 1
                    continue
                try:
                    content = base64.b64decode(str(item.get("data_base64") or ""), validate=True)
                except (ValueError, TypeError) as exc:
                    raise UserGalleryError(f"模板资源不是合法 Base64：{rel}") from exc
                total += len(content)
                if total > MAX_TOTAL_BYTES:
                    raise UserGalleryError("模板包总大小不能超过 24MB")
                target = staging.joinpath(*rel.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                copied += 1
                if rel.suffix.lower() in {".html", ".htm"}:
                    html_paths.append(rel)
                if rel.suffix.lower() in {".html", ".htm", ".css", ".js", ".mjs"}:
                    token_sources.append(content.decode("utf-8", errors="ignore"))
            if not html_paths:
                raise UserGalleryError("模板包至少需要一个 HTML 文件")
            requested_entry = _safe_relpath(entry) if entry else None
            if requested_entry and requested_entry not in html_paths:
                raise UserGalleryError("指定的入口 HTML 不在模板包中")
            selected = requested_entry or next(
                (item for item in html_paths if item.name.lower() == "index.html"),
                sorted(html_paths, key=lambda item: (len(item.parts), str(item)))[0],
            )
            html = staging.joinpath(*selected.parts).read_text(encoding="utf-8", errors="ignore")
            display_name = (name or _title(html, selected.stem)).strip()[:80]
            package_id = "user-" + _slug(display_name)
            target = self.root / package_id
            suffix = 2
            while target.exists():
                target = self.root / f"{package_id}-{suffix}"
                suffix += 1
            package_id = target.name
            if len(html_paths) > 1:
                pages = []
                for page_path in sorted(html_paths)[:40]:
                    page_html = staging.joinpath(*page_path.parts).read_text(encoding="utf-8", errors="ignore")
                    pages.append({"id": _slug(str(page_path.with_suffix(""))),
                                  "name": _title(page_html, page_path.stem), "file": str(page_path)})
            else:
                pages = _single_file_pages(html, str(selected))
            token_text = "\n".join(token_sources)
            colors = list(dict.fromkeys(value.upper() for value in HEX_RE.findall(token_text)))[:12]
            font_candidates = (_clean_text(value).strip('"\' ') for value in FONT_RE.findall(token_text))
            fonts = list(dict.fromkeys(
                value for value in font_candidates if value and len(value) <= 120 and "<" not in value and ">" not in value))[:8]
            intent = _intent(display_name, html, len(html_paths))
            for index, page in enumerate(pages):
                page["headline"] = page["name"]
                page["kicker"] = "PRIVATE TEMPLATE"
                page["block_id"] = _block_id(page["name"], intent, index)
            manifest = {
                "id": package_id, "name": display_name,
                "intent": intent,
                "preset_id": "fox-editorial-ink", "category": "private",
                "origin": "用户本地导入 · 不随项目上传", "description": f"{len(html_paths)} 个 HTML · {len(files)} 个文件",
                "source": "user", "entry": str(selected), "file": str(selected),
                "pages": pages, "tags": [str(tag)[:32] for tag in (tags or [])[:12]],
                "design_tokens": {"colors": colors, "font_families": fonts},
                "style_overrides": _style_overrides(colors, fonts),
                "file_count": copied, "ignored_files": ignored,
                "html_count": len(html_paths), "total_bytes": total,
                "usage_count": 0, "created_at": _now(), "last_used_at": None,
            }
            (staging / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            staging.replace(target)
            return manifest
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    def resolve_file(self, package_id: str, relative_path: str) -> Path:
        package = self.root / _package_id(package_id)
        rel = _safe_relpath(relative_path)
        target = package.joinpath(*rel.parts).resolve()
        if package.resolve() not in target.parents or not target.is_file():
            raise UserGalleryError("模板资源不存在")
        return target

    def delete(self, package_id: str) -> bool:
        try:
            target = self.root / _package_id(package_id)
        except UserGalleryError:
            return False
        if not target.is_dir():
            return False
        shutil.rmtree(target)
        return True

    def record_use(self, package_id: str) -> None:
        safe_id = _package_id(package_id)
        manifest = self.get(safe_id)
        manifest["usage_count"] = int(manifest.get("usage_count", 0)) + 1
        manifest["last_used_at"] = _now()
        path = self.root / safe_id / "manifest.json"
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
