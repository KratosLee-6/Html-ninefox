"""Project and workspace persistence for the local Web workbench."""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .. import pipeline, revisions

CANVAS_SCHEMA_VERSION = 1
WORKSPACE_FILE = ".workspace.json"
WORKSPACE_BACKUP_FILE = ".workspace.backup.json"
TRASH_DIR = ".trash"
MAX_WORKSPACE_BYTES = 2 * 1024 * 1024
_NAME_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class StoreError(Exception):
    def __init__(self, code: str, message: str, status: int = 400,
                 details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}


class ProjectStore:
    """Deep module for project directories and Canvas Schema v1 snapshots."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def list_projects(self, limit: int = 50) -> list[dict[str, Any]]:
        projects: list[dict[str, Any]] = []
        candidates = [path for path in self.root.iterdir()
                      if path.is_dir() and not path.name.startswith(".")]
        for path in sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                projects.append(self._project_meta(path))
            except StoreError:
                continue
            if len(projects) >= limit:
                break
        return projects

    def get_project(self, name: str) -> dict[str, Any]:
        return self._project_meta(self._existing_project(name))

    def resolve_project(self, name: str) -> Path:
        """Resolve a validated existing Project without reading its state."""
        return self._existing_project(name)

    def compare_revisions(self, name: str, from_revision: int | None = None,
                          to_revision: int | None = None) -> dict[str, Any]:
        """Return a bounded, metadata-rich diff between two HTML revisions."""
        project = self._existing_project(name)
        with revisions.project_lock(project):
            return self._compare_revisions(project, from_revision, to_revision)

    def revision_history(self, name: str) -> dict[str, Any]:
        project = self._existing_project(name)
        with revisions.project_lock(project):
            state = revisions.load_state(project)
            return {"ok": True, "current_revision": state.get("revision", 0),
                    "revisions": revisions.history(project, state)}

    def name_revision(self, name: str, revision: int, label: str) -> dict[str, Any]:
        project = self._existing_project(name)
        return {"ok": True, "revisions": revisions.name_revision(project, revision, label)}

    def restore_revision(self, name: str, revision: int, expected_revision: int) -> dict[str, Any]:
        project = self._existing_project(name)
        with revisions.project_lock(project):
            revisions.restore(project, revision, expected_revision)
            return {"ok": True, "project": self._project_meta(project)}

    def _compare_revisions(self, project: Path, from_revision: int | None,
                           to_revision: int | None) -> dict[str, Any]:
        state = revisions.load_state(project)
        current = state.get("revision", 0)
        available = revisions.available(project, state)
        if not available:
            raise StoreError("revision_not_found", "项目没有可比较的产物版本", 404)
        right = current if to_revision is None else to_revision
        left = max((revision for revision in available if revision < right), default=right) if from_revision is None else from_revision
        if left < 0 or right < 0 or left not in available or right not in available:
            raise StoreError("revision_not_found", "请求的产物版本不存在", 404,
                             {"available": sorted(available), "current": current})

        before, before_path = revisions.read_html(project, left, state)
        after, after_path = revisions.read_html(project, right, state)
        before_lines = before.splitlines(keepends=True)
        after_lines = after.splitlines(keepends=True)
        opcodes = difflib.SequenceMatcher(None, before_lines, after_lines).get_opcodes()
        added = sum(len(after_lines[j1:j2]) for tag, _, _, j1, j2 in opcodes if tag in {"insert", "replace"})
        removed = sum(len(before_lines[i1:i2]) for tag, i1, i2, _, _ in opcodes if tag in {"delete", "replace"})
        changed_blocks = sum(1 for tag, *_ in opcodes if tag == "replace")
        diff = "".join(difflib.unified_diff(
            before_lines, after_lines, fromfile=f"rev{left}.html", tofile=f"rev{right}.html", n=3,
        ))
        truncated = len(diff) > 50000
        return {
            "ok": True,
            "project_name": project.name,
            "current_revision": current,
            "revisions": revisions.history(project, state),
            "from_revision": left,
            "to_revision": right,
            "summary": {
                "same": before == after,
                "added_lines": added,
                "removed_lines": removed,
                "changed_blocks": changed_blocks,
                "before_bytes": len(before.encode("utf-8")),
                "after_bytes": len(after.encode("utf-8")),
            },
            "files": {"before": before_path.name, "after": after_path.name},
            "sha256": {
                "before": hashlib.sha256(before.encode("utf-8")).hexdigest(),
                "after": hashlib.sha256(after.encode("utf-8")).hexdigest(),
            },
            "diff": diff[:50000],
            "truncated": truncated,
        }

    def rename_project(self, name: str, new_name: str) -> dict[str, Any]:
        source = self._existing_project(name)
        target = self._project_path(new_name)
        if target.exists():
            raise StoreError("project_exists", f"项目已存在：{target.name}", 409)
        source.rename(target)
        return self._project_meta(target)

    def duplicate_project(self, name: str, new_name: str | None = None) -> dict[str, Any]:
        source = self._existing_project(name)
        target_name = self._validate_name(new_name) if new_name else self._next_copy_name(source.name)
        target = self._project_path(target_name)
        if target.exists():
            raise StoreError("project_exists", f"项目已存在：{target.name}", 409)
        shutil.copytree(source, target)
        state_path = target / pipeline.STATE_FILE
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["duplicated_from"] = source.name
            state["updated_at"] = datetime.now().isoformat(timespec="seconds")
            self._atomic_json(state_path, state)
        except (json.JSONDecodeError, OSError):
            pass
        return self._project_meta(target)

    def delete_project(self, name: str) -> dict[str, Any]:
        source = self._existing_project(name)
        trash = self.root / TRASH_DIR
        trash.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        target = trash / f"{stamp}-{source.name}"
        source.rename(target)
        return {"name": source.name, "deleted": True, "recoverable": True}

    def save_workspace(self, payload: dict[str, Any]) -> dict[str, Any]:
        snapshot = self._normalize_workspace(payload)
        target = self.root / WORKSPACE_FILE
        backup = self.root / WORKSPACE_BACKUP_FILE
        if target.exists():
            shutil.copy2(target, backup)
        self._atomic_json(target, snapshot)
        return {"saved": True, "schema_version": CANVAS_SCHEMA_VERSION,
                "saved_at": snapshot["saved_at"]}

    def load_workspace(self) -> dict[str, Any]:
        target = self.root / WORKSPACE_FILE
        backup = self.root / WORKSPACE_BACKUP_FILE
        if not target.exists() and not backup.exists():
            return {"exists": False, "schema_version": CANVAS_SCHEMA_VERSION}
        try:
            snapshot = self._read_workspace(target)
            return {"exists": True, "recovered": False, "state": snapshot}
        except StoreError as primary_error:
            if not backup.exists():
                raise primary_error
            snapshot = self._read_workspace(backup)
            return {"exists": True, "recovered": True, "state": snapshot}

    def _project_meta(self, path: Path) -> dict[str, Any]:
        state_path = path / pipeline.STATE_FILE
        if not state_path.is_file():
            raise StoreError("project_state_missing", f"项目缺少 {pipeline.STATE_FILE}", 409)
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise StoreError("project_state_invalid", f"项目状态损坏：{path.name}", 409) from exc
        output = path / "output.html"
        return {
            "name": path.name,
            "project": str(path),
            "prompt": state.get("prompt", "")[:120],
            "intent": state.get("intent", ""),
            "preset_id": state.get("preset_id", ""),
            "revision": state.get("revision", 0),
            "created_at": state.get("created_at", ""),
            "updated_at": state.get("updated_at", state.get("created_at", "")),
            "preview_url": f"/output/{path.name}/output.html" if output.is_file() else None,
            "recipe_run": state.get("recipe_run"),
            "verification": state.get("verification"),
            "memory_applied": state.get("memory_applied"),
            "files": sorted(item.name for item in path.iterdir() if item.is_file()),
        }

    def _existing_project(self, name: str) -> Path:
        path = self._project_path(name)
        if not path.is_dir():
            raise StoreError("project_not_found", f"项目不存在：{path.name}", 404)
        return path

    def _project_path(self, name: str) -> Path:
        safe_name = self._validate_name(name)
        path = (self.root / safe_name).resolve()
        if not path.is_relative_to(self.root):
            raise StoreError("project_name_invalid", "项目名称越出工作目录", 400)
        return path

    def _validate_name(self, value: str | None) -> str:
        name = (value or "").strip()
        if not name or name in {".", ".."} or name.startswith("."):
            raise StoreError("project_name_invalid", "项目名称不能为空或以点开头", 400)
        if len(name) > 80 or _NAME_INVALID.search(name):
            raise StoreError("project_name_invalid", "项目名称包含非法字符或超过 80 字符", 400)
        return name

    def _next_copy_name(self, name: str) -> str:
        for index in range(1, 1000):
            suffix = "-copy" if index == 1 else f"-copy-{index}"
            candidate = f"{name[:80-len(suffix)]}{suffix}"
            if not (self.root / candidate).exists():
                return candidate
        raise StoreError("project_copy_limit", "无法分配项目副本名称", 409)

    def _normalize_workspace(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise StoreError("workspace_invalid", "工作区快照必须是对象", 400)
        schema_version = payload.get("schema_version", CANVAS_SCHEMA_VERSION)
        if schema_version != CANVAS_SCHEMA_VERSION:
            raise StoreError("workspace_schema_unsupported", "不支持的工作区版本", 409,
                             {"supported": [CANVAS_SCHEMA_VERSION], "received": schema_version})
        canvas = payload.get("canvas")
        if not isinstance(canvas, dict):
            raise StoreError("workspace_invalid", "工作区缺少 canvas", 400)
        nodes = canvas.get("nodes")
        edges = canvas.get("edges")
        camera = canvas.get("camera")
        if not isinstance(nodes, list) or not isinstance(edges, list) or not isinstance(camera, dict):
            raise StoreError("workspace_invalid", "camera、nodes、edges 类型不正确", 400)
        if len(nodes) > 500 or len(edges) > 1000:
            raise StoreError("workspace_too_complex", "工作区节点或连线数量超限", 413,
                             {"max_nodes": 500, "max_edges": 1000})
        snapshot = {
            "schema_version": CANVAS_SCHEMA_VERSION,
            "saved_at": datetime.now().isoformat(timespec="milliseconds"),
            "canvas": canvas,
        }
        encoded = json.dumps(snapshot, ensure_ascii=False).encode("utf-8")
        if len(encoded) > MAX_WORKSPACE_BYTES:
            raise StoreError("workspace_too_large", "工作区快照超过 2MB", 413)
        return snapshot

    def _read_workspace(self, path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise StoreError("workspace_corrupt", "工作区快照损坏", 409) from exc
        return self._normalize_loaded_workspace(payload)

    def _normalize_loaded_workspace(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("schema_version") != CANVAS_SCHEMA_VERSION:
            raise StoreError("workspace_schema_unsupported", "工作区版本无法读取", 409)
        canvas = payload.get("canvas")
        if not isinstance(canvas, dict) or not isinstance(canvas.get("nodes"), list):
            raise StoreError("workspace_corrupt", "工作区内容不完整", 409)
        return payload

    @staticmethod
    def _atomic_json(path: Path, data: dict[str, Any]) -> None:
        temp = path.with_name(path.name + ".tmp")
        body = json.dumps(data, ensure_ascii=False, indent=2)
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
