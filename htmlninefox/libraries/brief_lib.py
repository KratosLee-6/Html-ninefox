"""brief_lib.py · Brief 库 CRUD（v0.2 · 三重沉淀之一）

Brief 标准 v0.1 JSON Schema（5 必填字段 + 轻量校验，无外部依赖）：
  goal / context / content / style / constraints
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

BRIEF_DIR = Path.home() / ".htmlninefox" / "briefs"

REQUIRED_FIELDS = ("goal", "context", "content", "style", "constraints")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _ensure() -> None:
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)


def _validate(brief: Dict[str, Any]) -> List[str]:
    """返回错误列表（空 = 通过）。"""
    if not isinstance(brief, dict):
        return ["brief 必须是 object"]
    errs = [f"missing required field: {k}" for k in REQUIRED_FIELDS if k not in brief]
    palette = (brief.get("style") or {}).get("palette") or {}
    errs += [f"style.palette.{k} 不是合法 hex: {v}" for k, v in palette.items()
             if isinstance(v, str) and not HEX_RE.match(v)]
    return errs


def _to_meta(brief_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    b = data.get("brief", data) if isinstance(data, dict) else {}
    goal = b.get("goal") if isinstance(b, dict) else {}
    return {
        "id": brief_id,
        "goal": goal.get("job_to_be_done") if isinstance(goal, dict) else "",
        "updated_at": data.get("_persisted_at") or data.get("updated_at") or "",
    }


class BriefLib:
    """Brief 库 CRUD 入口（v0.2 · schema 校验 + search）。"""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir) if base_dir else BRIEF_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def list(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for p in sorted(self.base_dir.glob("*.json")):
            try:
                out.append(_to_meta(p.stem, json.loads(p.read_text(encoding="utf-8"))))
            except (json.JSONDecodeError, OSError):
                continue
        return out

    def get(self, brief_id: str) -> Optional[Dict[str, Any]]:
        path = self.base_dir / f"{brief_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def add(self, md_path: str | Path) -> Dict[str, Any]:
        """从 Markdown 添加：解析第一行 # → goal，写入 JSON。返回 {id, valid, errors}。"""
        md = Path(md_path)
        text = md.read_text(encoding="utf-8")
        first = text.split("\n", 1)[0].strip()
        goal_text = re.sub(r"^#+\s*", "", first) or md.stem

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        brief_id = f"{ts}-{md.stem}"[:80]

        brief = {
            "goal": {"job_to_be_done": goal_text},
            "context": {"device": "通用"},
            "content": {"must_have": []},
            "style": {"tone": "（fallback）", "reference": []},
            "constraints": {"forbidden": [], "technical": []},
        }
        errors = _validate(brief)
        payload = {
            "id": brief_id,
            "brief": brief,
            "confidence": 0.3,
            "missing_fields": list(REQUIRED_FIELDS),
            "source": str(md),
            "raw_md": text,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "validation_errors": errors,
        }
        (self.base_dir / f"{brief_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"id": brief_id, "valid": len(errors) == 0, "errors": errors}

    def delete(self, brief_id: str) -> bool:
        path = self.base_dir / f"{brief_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def search(self, keyword: str) -> List[Dict[str, Any]]:
        """关键词搜索：扫 raw_md / goal / source。"""
        kw = keyword.lower()
        hits: List[Dict[str, Any]] = []
        for meta in self.list():
            data = self.get(meta["id"]) or {}
            blob = json.dumps(data, ensure_ascii=False).lower()
            if kw in blob:
                hits.append(meta)
        return hits
