"""Curated, real-HTML template gallery with page-level extraction."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

GALLERY_ROOT = Path(__file__).resolve().parent / "templates" / "gallery"
MANIFEST_PATH = GALLERY_ROOT / "manifest.json"


@lru_cache(maxsize=1)
def _manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def list_gallery() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw in _manifest().get("items", []):
        item = dict(raw)
        item_id = item["id"]
        item["preview_url"] = f"/api/gallery-preview?id={item_id}"
        item["pages"] = [
            {
                **page,
                "preview_url": f"/api/gallery-preview?id={item_id}&page={page['id']}",
            }
            for page in item.get("pages", [])
        ]
        items.append(item)
    return items


def get_gallery_item(item_id: str) -> dict[str, Any]:
    item = next((item for item in list_gallery() if item["id"] == item_id), None)
    if not item:
        raise ValueError(f"模板作品不存在：{item_id}")
    return item


def render_gallery_preview(item_id: str, page_id: str | None = None) -> str:
    item = get_gallery_item(item_id)
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


def recommend_gallery(intent: str, preset_id: str | None = None) -> dict[str, Any]:
    items = list_gallery()
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
