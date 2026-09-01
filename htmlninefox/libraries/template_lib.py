"""template_lib.py · 审美模板库 CRUD（v0.2 · 三重沉淀之二）

模板 Schema：{id, name, html_path, tags, created_at, description, design_tokens}
来源：内置 PRESETS（generators._tokens）+ 用户 ~/.htmlninefox/templates/<id>/
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

TEMPLATE_DIR = Path.home() / ".htmlninefox" / "templates"
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _ensure() -> None:
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)


def _builtin_meta(pid: str, p: Dict[str, Any]) -> Dict[str, Any]:
    name = p.get("name", pid)
    return {
        "id": pid, "name": name,
        "html_path": f"builtin://{pid}",
        "tags": list(p.get("match_keywords", [])),
        "created_at": "2026-08-01T00:00:00",
        "description": name.split("·", 1)[-1].strip()[:80],
        "design_tokens": dict(p.get("tokens", {})),
        "source": "builtin",
    }


def _user_meta(d: Path) -> Optional[Dict[str, Any]]:
    sj = d / "style.json"
    if not sj.exists():
        return None
    try:
        data = json.loads(sj.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return {
        "id": d.name, "name": data.get("name", d.name),
        "html_path": data.get("html_path", str(d / "index.html")),
        "tags": list(data.get("tags", [])),
        "created_at": data.get("created_at", "2026-08-29T00:00:00"),
        "description": data.get("description", ""),
        "design_tokens": dict(data.get("tokens", {})),
        "source": "user",
    }


class TemplateLib:
    """审美模板库 CRUD 入口（v0.2 · 内置 + 用户）。"""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir) if base_dir else TEMPLATE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        # 延迟导入：避免循环引用
        from ..generators import _tokens as _tk
        self._PRESETS = _tk.PRESETS

    def list(self) -> List[Dict[str, Any]]:
        items = [_builtin_meta(pid, p) for pid, p in self._PRESETS.items()]
        if not self.base_dir.is_dir():
            return items
        for d in sorted(self.base_dir.iterdir()):
            meta = _user_meta(d) if d.is_dir() else None
            if meta:
                items.append(meta)
        return items

    def get(self, template_id: str) -> Optional[Dict[str, Any]]:
        return next((t for t in self.list() if t["id"] == template_id), None)

    def add(self, html_path: str | Path, name: str,
            tags: Optional[List[str]] = None, description: str = "") -> Dict[str, Any]:
        html = Path(html_path)
        slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", name).strip("-")[:40] or html.stem
        target = self.base_dir / slug
        if target.exists():
            slug = f"{slug}-{datetime.now().strftime('%H%M%S')}"
            target = self.base_dir / slug
        target.mkdir(parents=True, exist_ok=True)
        # 扫 HTML 里的 hex 颜色作为 design_tokens
        hexes = []
        if html.exists():
            hexes = list({m.group(0).upper() for m in HEX_RE.finditer(html.read_text(encoding="utf-8", errors="ignore"))})

        tokens: Dict[str, Any] = {"primary": next(iter(hexes), "#5E6AD2")} if hexes else {}
        meta = {
            "name": name,
            "html_path": str(html),
            "tags": tags or [html.stem],
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "description": description or f"From {html.name}",
            "tokens": tokens,
        }
        (target / "style.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"id": slug, "valid": True}

    def delete(self, template_id: str) -> bool:
        if template_id in self._PRESETS:
            return False
        target = self.base_dir / template_id
        if not (target.exists() and target.is_dir()):
            return False
        import shutil
        shutil.rmtree(target)
        return True

    def search_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        tag_l = tag.lower()
        return [t for t in self.list() if any(tag_l in tg.lower() for tg in t.get("tags", []))]
