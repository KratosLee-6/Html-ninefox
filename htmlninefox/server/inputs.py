"""Local input attachment storage for text, document, and image context."""

from __future__ import annotations

import base64
import binascii
import json
import re
import uuid
from pathlib import Path
from typing import Any

MAX_INPUT_BYTES = 8 * 1024 * 1024
TEXT_SUFFIXES = {".txt", ".md", ".json", ".csv", ".html", ".htm", ".xml", ".yaml", ".yml"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
_SAFE_NAME = re.compile(r"[^\w.\-\u4e00-\u9fff]+", re.UNICODE)


class InputError(ValueError):
    pass


class InputStore:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve() / ".inputs"

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = self._safe_name(str(payload.get("name") or "input.bin"))
        mime = str(payload.get("mime") or "application/octet-stream")[:120]
        encoded = str(payload.get("data_base64") or "")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise InputError("附件数据不是合法 Base64") from exc
        if not data:
            raise InputError("附件内容为空")
        if len(data) > MAX_INPUT_BYTES:
            raise InputError("单个附件不能超过 8MB")
        input_id = uuid.uuid4().hex
        folder = self.root / input_id
        folder.mkdir(parents=True, exist_ok=False)
        source = folder / name
        source.write_bytes(data)
        suffix = source.suffix.lower()
        kind = "image" if suffix in IMAGE_SUFFIXES or mime.startswith("image/") else "document"
        excerpt = ""
        if suffix in TEXT_SUFFIXES or mime.startswith("text/"):
            excerpt = data.decode("utf-8", errors="replace")[:4000]
            kind = "text"
        meta = {
            "id": input_id,
            "name": name,
            "mime": mime,
            "size": len(data),
            "kind": kind,
            "excerpt": excerpt,
        }
        (folder / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return meta

    def describe(self, input_ids: list[str]) -> list[dict[str, Any]]:
        results = []
        for input_id in input_ids[:12]:
            if not re.fullmatch(r"[0-9a-f]{32}", str(input_id)):
                continue
            meta_path = self.root / str(input_id) / "meta.json"
            if not meta_path.is_file():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(meta, dict):
                results.append(meta)
        return results

    @staticmethod
    def prompt_context(items: list[dict[str, Any]]) -> str:
        if not items:
            return ""
        lines = ["\n\n[用户附件上下文]"]
        for item in items:
            lines.append(f"- {item.get('name')} · {item.get('kind')} · {item.get('mime')} · {item.get('size')} bytes")
            excerpt = str(item.get("excerpt") or "").strip()
            if excerpt:
                lines.append("  内容摘录：" + excerpt[:1200].replace("\n", " "))
        return "\n".join(lines)

    @staticmethod
    def _safe_name(value: str) -> str:
        name = Path(value).name.strip()[:100]
        name = _SAFE_NAME.sub("-", name).strip(".-")
        return name or "input.bin"
