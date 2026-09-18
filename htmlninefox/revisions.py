"""Local artifact history shared by the pipeline and HTTP adapter."""

from __future__ import annotations

import copy
import json
import os
import re
import tempfile
import threading
from datetime import datetime
from functools import wraps
from pathlib import Path

STATE_FILE = ".foxstate.json"
MAX_HTML_BYTES = 2 * 1024 * 1024
_locks = [threading.RLock() for _ in range(64)]


class RevisionError(ValueError):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code, self.status = code, status


def project_lock(project):
    return _locks[hash(str(Path(project).resolve()).casefold()) % len(_locks)]


def locked_project(function):
    @wraps(function)
    def wrapped(project, *args, **kwargs):
        with project_lock(project):
            return function(project, *args, **kwargs)
    return wrapped


def safe_path(project: Path, relative: str) -> Path:
    path = project / relative
    if not path.resolve().is_relative_to(project.resolve()):
        raise RevisionError("revision_forbidden", "版本文件越出项目目录", 403)
    return path


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("not an object")
        return value
    except (OSError, ValueError) as exc:
        raise RevisionError("project_state_invalid", "项目或版本状态损坏") from exc


def load_state(project: Path) -> dict:
    state = _read_json(safe_path(project, STATE_FILE))
    value = state.get("revision", 0)
    if type(value) is not int or value < 0:
        raise RevisionError("project_state_invalid", "项目版本号无效")
    return state


def atomic_write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".revision-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _write_json(path: Path, value: dict) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2))


def available(project: Path, state: dict) -> list[int]:
    directory = safe_path(project, "revisions")
    numbers = {int(match[1]) for path in directory.glob("rev*.html")
               if (match := re.fullmatch(r"rev(0|[1-9]\d*)\.html", path.name))
               and path.is_file()}
    if safe_path(project, "output.html").is_file():
        numbers.add(state.get("revision", 0))
    return sorted(numbers)


def read_html(project: Path, revision: int, state: dict) -> tuple[str, Path]:
    if type(revision) is not int or revision < 0:
        raise RevisionError("revision_invalid", "版本必须是非负整数", 400)
    path = safe_path(project, f"revisions/rev{revision}.html")
    if revision == state.get("revision", 0) and safe_path(project, "output.html").is_file():
        path = safe_path(project, "output.html")
    if not path.is_file():
        raise RevisionError("revision_not_found", f"rev{revision} 不存在", 404)
    if path.stat().st_size > MAX_HTML_BYTES:
        raise RevisionError("revision_too_large", "版本超过 2MB，无法在线处理", 413)
    try:
        # Keep CRLF and lone CR intact: restoring must preserve the artifact bytes.
        with path.open(encoding="utf-8", newline="") as handle:
            return handle.read(), path
    except UnicodeError as exc:
        raise RevisionError("revision_encoding_invalid", "版本文件不是有效的 UTF-8", 422) from exc


def _record(project: Path, revision: int) -> dict:
    path = safe_path(project, f"revisions/rev{revision}.json")
    return _read_json(path) if path.is_file() else {}


def history(project: Path, state: dict | None = None) -> list[dict]:
    state = state if state is not None else load_state(project)
    current = state.get("revision", 0)
    result = []
    for number in available(project, state):
        record = _record(project, number)
        path = safe_path(project, "output.html" if number == current else f"revisions/rev{number}.html")
        if not path.is_file():
            path = safe_path(project, f"revisions/rev{number}.html")
        result.append({
            "revision": number, "label": record.get("label", ""),
            "parent_revision": record.get("parent_revision"),
            "restored_from": record.get("restored_from"),
            "kind": record.get("kind", "legacy"),
            "created_at": record.get("created_at", ""),
            "is_current": number == current, "bytes": path.stat().st_size,
            "can_restore": isinstance(record.get("state"), dict) and number != current,
        })
    return result


def snapshot(project: Path, state: dict, html: str, *, kind="generate",
             parent_revision=None, restored_from=None) -> None:
    number = state.get("revision", 0)
    atomic_write(safe_path(project, f"revisions/rev{number}.html"), html)
    _write_json(safe_path(project, f"revisions/rev{number}.json"), {
        "revision": number, "parent_revision": parent_revision,
        "restored_from": restored_from, "kind": kind, "label": "",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "state": copy.deepcopy(state),
    })


def commit(project: Path, before: dict, after: dict, html: str, *, kind: str,
           restored_from=None) -> dict:
    """Append history; compensate an interrupted write without losing the old output."""
    current = before.get("revision", 0)
    old_html, _ = read_html(project, current, before)
    if not isinstance(_record(project, current).get("state"), dict):
        label = _record(project, current).get("label", "")
        snapshot(project, before, old_html, kind="checkpoint")
        if label:
            record = _record(project, current)
            record["label"] = label
            _write_json(safe_path(project, f"revisions/rev{current}.json"), record)
    after = copy.deepcopy(after)
    after["revision"] = max(available(project, before), default=current) + 1
    after["updated_at"] = datetime.now().isoformat(timespec="seconds")
    new_number = after["revision"]
    try:
        snapshot(project, after, html, kind=kind, parent_revision=current, restored_from=restored_from)
        atomic_write(safe_path(project, "output.html"), html)
        _write_json(safe_path(project, STATE_FILE), after)
    except Exception:
        atomic_write(safe_path(project, "output.html"), old_html)
        _write_json(safe_path(project, STATE_FILE), before)
        for extension in ("html", "json"):
            safe_path(project, f"revisions/rev{new_number}.{extension}").unlink(missing_ok=True)
        raise
    return after


@locked_project
def name_revision(project: Path, revision: int, label: str) -> list[dict]:
    state = load_state(project)
    read_html(project, revision, state)
    if not isinstance(label, str) or len(label.strip()) > 80 or any(ord(char) < 32 for char in label):
        raise RevisionError("revision_label_invalid", "版本名称最多 80 字符，不能包含控制字符", 400)
    record = _record(project, revision)
    record["label"] = label.strip()
    _write_json(safe_path(project, f"revisions/rev{revision}.json"), record)
    return history(project, state)


@locked_project
def restore(project: Path, revision: int, expected_revision: int) -> dict:
    before = load_state(project)
    if type(expected_revision) is not int or expected_revision < 0:
        raise RevisionError("revision_invalid", "需要当前版本号以防覆盖更新", 400)
    if before.get("revision", 0) != expected_revision:
        raise RevisionError("revision_conflict", "项目已有新版本，请刷新版本列表后重试")
    html, _ = read_html(project, revision, before)
    if revision == expected_revision:
        raise RevisionError("revision_already_current", "该版本已是当前版本")
    record = _record(project, revision)
    if not isinstance(record.get("state"), dict):
        raise RevisionError("revision_state_missing", "旧版本缺少生成配置，仅支持查看差异，无法完整恢复")
    after = copy.deepcopy(record["state"])
    # Adoption remains an explicit user action; restoration never changes memory.
    after.pop("memory_adoption", None)
    after["verification"] = None
    after["recipe_run"] = None
    return commit(project, before, after, html, kind="restore", restored_from=revision)
