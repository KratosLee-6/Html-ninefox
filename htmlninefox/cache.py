"""cache.py · 磁盘 JSON 缓存（复用 PoC v0.1）"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_CACHE_DIR = Path.home() / ".htmlninefox" / "cache" / "llm"
DEFAULT_TTL_SECONDS = 7 * 24 * 3600


def _cache_key(prompt: str, model: str, task: str) -> str:
    raw = f"{task}::{model}::{prompt}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class DiskCache:
    def __init__(
        self,
        cache_dir: str | Path | None = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        enabled: bool = True,
    ):
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.ttl_seconds = ttl_seconds
        self.enabled = enabled
        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.cache_dir / key[:2] / f"{key}.json"

    def get(self, prompt: str, model: str, task: str) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        path = self._path(_cache_key(prompt, model, task))
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                entry = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
        if time.time() - entry.get("created_at", 0) > self.ttl_seconds:
            try:
                path.unlink()
            except OSError:
                pass
            return None
        return entry.get("value")

    def set(self, prompt: str, model: str, task: str, value: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        key = _cache_key(prompt, model, task)
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "created_at": time.time(),
            "key": key,
            "model": model,
            "task": task,
            "value": value,
        }
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)
        tmp.replace(path)

    def clear(self) -> int:
        if not self.cache_dir.exists():
            return 0
        count = 0
        for p in self.cache_dir.rglob("*.json"):
            try:
                p.unlink()
                count += 1
            except OSError:
                pass
        return count

    def stats(self) -> Dict[str, Any]:
        if not self.cache_dir.exists():
            return {"files": 0, "size_bytes": 0}
        files = list(self.cache_dir.rglob("*.json"))
        size = sum(p.stat().st_size for p in files)
        return {"files": len(files), "size_bytes": size}
