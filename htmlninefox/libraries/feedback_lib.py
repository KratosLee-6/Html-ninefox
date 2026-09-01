"""feedback_lib.py · 反馈沉淀库 v0.2 (Day 13-14 · 三重沉淀之三)

按 schema 校验 + JSON 文件沉淀（与 brief_lib / template_lib 风格一致）：
  ~/.htmlninefox/feedback/<feedback_id>.json
schema 必填：target_element / suggestion / confidence / actionable
可选字段：tokens_extracted（深 merge）
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

FEEDBACK_DIR = Path.home() / ".htmlninefox" / "feedback"

REQUIRED_KEYS = ("target_element", "suggestion", "confidence", "actionable")


def _ensure() -> None:
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)


def _validate(data: Dict[str, Any]) -> List[str]:
    """返回错误列表（空 = 通过）。"""
    errs = [f"missing required field: {k}" for k in REQUIRED_KEYS if k not in data]
    conf = data.get("confidence")
    if conf is not None and not isinstance(conf, (int, float)):
        errs.append(f"confidence 必须是数字，得到 {type(conf).__name__}")
    return errs


def _to_meta(feedback_id: str, project_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """构造持久化的 meta dict（保留 tokens_extracted + 时间戳）。"""
    return {
        "id": feedback_id,
        "project_id": project_id,
        "target_element": data.get("target_element", "global"),
        "suggestion": data.get("suggestion", ""),
        "confidence": float(data.get("confidence", 0.5)),
        "actionable": bool(data.get("actionable", False)),
        "rules": list(data.get("rules", []) or []),
        "tokens_extracted": dict(data.get("tokens_extracted", {}) or {}),
        "raw_note": data.get("raw_note", ""),
        "_model": data.get("_model", "rules"),
        "_persisted_at": datetime.now().isoformat(timespec="seconds"),
    }


class FeedbackLib:
    """反馈沉淀库 CRUD 入口（v0.2 · JSON-per-feedback + token 累计）。"""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir) if base_dir else FEEDBACK_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def append(self, project_id: str, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """追加一条反馈 → 返回 {id, valid, errors}。"""
        errs = _validate(feedback)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        fid = f"{ts}-{uuid.uuid4().hex[:8]}"
        meta = _to_meta(fid, project_id, feedback)
        (self.base_dir / f"{fid}.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("[feedback_lib] appended → %s.json", fid)
        return {"id": fid, "valid": len(errs) == 0, "errors": errs}

    def list(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """列反馈（可选按 project_id 过滤）。按 mtime 升序，最新文件后追加 → 深 merge 时最新值覆盖。"""
        out: List[Dict[str, Any]] = []
        files = sorted(self.base_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        for p in files:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if project_id is None or data.get("project_id") == project_id:
                out.append(data)
        return out

    def get(self, feedback_id: str) -> Optional[Dict[str, Any]]:
        path = self.base_dir / f"{feedback_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def delete(self, feedback_id: str) -> bool:
        path = self.base_dir / f"{feedback_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def get_tokens_extracted(self, project_id: str) -> Dict[str, Any]:
        """累积项目所有 feedback 的 tokens_extracted（深 merge，最新覆盖）。"""
        merged: Dict[str, Any] = {}
        for fb in self.list(project_id):
            tokens = fb.get("tokens_extracted") or {}
            for category, vals in tokens.items():
                if category not in merged:
                    merged[category] = {}
                if isinstance(vals, dict) and isinstance(merged[category], dict):
                    merged[category].update(vals)
                else:
                    merged[category] = vals
        return merged
