"""Curated, real-HTML template gallery with page-level extraction."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .user_gallery import UserGalleryError, UserGalleryStore

GALLERY_ROOT = Path(__file__).resolve().parent / "templates" / "gallery"
MANIFEST_PATH = GALLERY_ROOT / "manifest.json"


@lru_cache(maxsize=1)
def _manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def list_gallery(user_root: str | Path | None = None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    raw_items = list(_manifest().get("items", []))
    if user_root is not None:
        raw_items.extend(UserGalleryStore(user_root).list())
    for raw in raw_items:
        item = dict(raw)
        item_id = item["id"]
        encoded_id = quote(item_id)
        item["preview_url"] = f"/api/gallery-preview?id={encoded_id}"
        item["pages"] = [
            {
                **page,
                "preview_url": f"/api/gallery-preview?id={encoded_id}&page={quote(page['id'])}",
            }
            for page in item.get("pages", [])
        ]
        items.append(item)
    return items


def get_gallery_item(item_id: str, user_root: str | Path | None = None) -> dict[str, Any]:
    item = next((item for item in list_gallery(user_root) if item["id"] == item_id), None)
    if not item:
        raise ValueError(f"模板作品不存在：{item_id}")
    return item


def render_gallery_preview(item_id: str, page_id: str | None = None,
                           user_root: str | Path | None = None) -> str:
    item = get_gallery_item(item_id, user_root)
    if item.get("source") == "user":
        if user_root is None:
            raise ValueError("私人模板目录不可用")
        page = next((entry for entry in item.get("pages", []) if entry["id"] == page_id), None)
        if page_id and page is None:
            raise ValueError(f"模板页面不存在：{page_id}")
        relative_file = (page or {}).get("file") or item.get("entry") or item["file"]
        try:
            source = UserGalleryStore(user_root).resolve_file(item_id, relative_file)
        except UserGalleryError as exc:
            raise ValueError(str(exc)) from exc
        html = source.read_text(encoding="utf-8", errors="ignore")
        parent = Path(relative_file).parent.as_posix().strip("./")
        base = f"/api/gallery-assets/{quote(item_id)}/"
        if parent:
            base += "/".join(quote(part) for part in parent.split("/")) + "/"
        base_tag = f'<base href="{base}"><meta name="htmlninefox-private-template" content="{quote(item_id)}">'
        if re.search(r"</head>", html, re.I):
            html = re.sub(r"</head>", base_tag + "</head>", html, count=1, flags=re.I)
        else:
            doctype = re.match(r"\s*<!doctype[^>]*>", html, re.I)
            html = html[:doctype.end()] + base_tag + html[doctype.end():] if doctype else base_tag + html
        if page and page.get("selector"):
            selector = json.dumps(page["selector"], ensure_ascii=False)
            index = int(page.get("index", 0))
            isolated = (
                "<style>.nav,.counter{display:none!important}body{overflow:hidden!important}</style>"
                "<script>addEventListener('DOMContentLoaded',()=>{"
                f"const nodes=document.querySelectorAll({selector});"
                "nodes.forEach(n=>{n.style.display='none';n.style.opacity='0'});"
                f"const n=nodes[{index}];"
                "if(n){n.style.setProperty('display','grid','important');n.style.setProperty('opacity','1','important');"
                "n.style.setProperty('transform','none','important');n.style.setProperty('pointer-events','auto','important')}});"
                "</script>"
            )
            if re.search(r"</body>", html, re.I):
                html = re.sub(r"</body>", isolated + "</body>", html, count=1, flags=re.I)
            else:
                html += isolated
        return html
    source = GALLERY_ROOT / item["file"]
    html = source.read_text(encoding="utf-8")
    if not page_id:
        return html
    if page_id not in {page["id"] for page in item.get("pages", [])}:
        raise ValueError(f"模板页面不存在：{page_id}")
    isolated_css = (
        "<style>body{overflow:hidden!important}.page{display:none!important;opacity:0!important;}"
        f'.page[data-page="{page_id}"]{{display:grid!important;opacity:1!important;transform:none!important;pointer-events:auto!important;}}'
        ".nav,.counter{display:none!important}</style>"
    )
    return html.replace("</head>", isolated_css + "</head>", 1)


def recommend_gallery(intent: str, preset_id: str | None = None,
                      user_root: str | Path | None = None) -> dict[str, Any]:
    items = list_gallery(user_root)
    learned = sorted(
        (item for item in items if item.get("source") == "user"
         and item.get("intent") == intent and int(item.get("usage_count", 0)) > 0),
        key=lambda item: (int(item.get("usage_count", 0)), item.get("last_used_at") or ""),
        reverse=True,
    )
    if learned:
        return learned[0]
    if preset_id == "fox-swiss-signal":
        preferred = "guizang-swiss-signal"
    elif intent == "landing" and preset_id == "fox-pixel-garden":
        preferred = "pixel-garden-product"
    elif intent == "landing":
        preferred = "guizang-dune-portfolio"
    elif preset_id == "guizang-magazine":
        preferred = "guizang-editorial-ink"
    else:
        preferred = "guizang-indigo-research"
    selected = next((item for item in items if item["id"] == preferred), None)
    if selected is None:
        selected = next((item for item in items if item["intent"] == intent), items[0])
    return selected
