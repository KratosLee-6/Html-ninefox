"""Local AI provider settings with secret-safe API responses."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

SETTINGS_DIR = ".settings"
AI_SETTINGS_FILE = "ai.json"
DEFAULTS = {
    "enabled": False,
    "provider": "openai-compatible",
    "model": "",
    "base_url": "",
    "api_key": "",
}


class AISettingsStore:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.path = self.root / SETTINGS_DIR / AI_SETTINGS_FILE

    def load(self) -> dict[str, Any]:
        data = dict(DEFAULTS)
        if self.path.is_file():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    data.update({key: loaded.get(key, data[key]) for key in DEFAULTS})
            except (json.JSONDecodeError, OSError):
                pass
        return data

    def public(self) -> dict[str, Any]:
        data = self.load()
        return {
            "enabled": bool(data.get("enabled")),
            "provider": data.get("provider") or "openai-compatible",
            "model": data.get("model") or "",
            "base_url": data.get("base_url") or "",
            "api_key_set": bool(data.get("api_key")),
            "storage": "local-only",
        }

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.load()
        api_key = str(payload.get("api_key") or "").strip()
        if payload.get("clear_api_key"):
            current["api_key"] = ""
        elif api_key:
            current["api_key"] = api_key
        for key in ("provider", "model", "base_url"):
            if key in payload:
                current[key] = str(payload.get(key) or "").strip()
        if "enabled" in payload:
            current["enabled"] = bool(payload.get("enabled"))
        if current["enabled"] and (not current["model"] or not current["base_url"]):
            raise ValueError("启用 AI 前需要填写模型名称和 API Base URL")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass
        os.environ["HTMLNINEFOX_AI_SETTINGS"] = str(self.path)
        return self.public()

    def activate(self) -> dict[str, Any]:
        os.environ["HTMLNINEFOX_AI_SETTINGS"] = str(self.path)
        return self.load()
