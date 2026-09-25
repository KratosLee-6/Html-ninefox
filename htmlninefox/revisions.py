"""Local artifact history shared by the pipeline and HTTP adapter."""

from __future__ import annotations

import copy
import json
import re
import threading
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from pathlib import Path

from .durable import LockBusyError, acquire_file_lock, atomic_write, release_file_lock

STATE_FILE = ".foxstate.json"
JOURNAL_FILE = ".commit-journal.json"
LOCK_DIR = ".locks"
LOCK_TIMEOUT_SECONDS = 15.0
MAX_HTML_BYTES = 2 * 1024 * 1024
_locks = [threading.RLock() for _ in range(64)]
_lock_depth = threading.local()
_lock_handles: dict[str, object] = {}


class RevisionError(ValueError):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code, self.status = code, status


def lock_file(project: Path) -> Path:
    """Cross-process lock file, kept outside the Project directory.

    Windows refuses to rename a directory that contains an open handle, so
    rename and delete hold this sibling lock instead of an in-project file.
    """
    resolved = Path(project).resolve()
    return resolved.parent / LOCK_DIR / f"{resolved.name}.lock"


@contextmanager
def project_lock(project):
    """Serialize Project access in-process and across processes.

    The striped RLock orders threads inside one process; the outermost holder
    of a given project also takes the cross-process file lock so CLI and
    server processes cannot interleave a multi-file commit.
    """
    resolved = Path(project).resolve()
    key = str(resolved).casefold()
    with _locks[hash(key) % len(_locks)]:
        depths = getattr(_lock_depth, "depths", None)
        if depths is None:
            depths = {}
            _lock_depth.depths = depths
        if depths.get(key, 0) == 0:
            try:
                _lock_handles[key] = acquire_file_lock(
                    lock_file(resolved), timeout=LOCK_TIMEOUT_SECONDS)
            except LockBusyError as error:
                raise RevisionError(
                    "project_busy", "项目正被另一个进程修改，请稍后重试") from error
        depths[key] = depths.get(key, 0) + 1
        try:
            yield
        finally:
            depths[key] -= 1
            if depths[key] <= 0:
                depths.pop(key, None)
                handle = _lock_handles.pop(key, None)
                if handle is not None:
                    release_file_lock(handle)


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
    if safe_path(project, JOURNAL_FILE).is_file():
        with project_lock(project):
            _recover_interrupted_commit(project, state)
    return state


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


def _write_journal(project: Path, target: int, kind: str, parent: int) -> None:
    _write_json(safe_path(project, JOURNAL_FILE), {
        "schema_version": 1,
        "target_revision": target,
        "parent_revision": parent,
        "kind": kind,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })


def _clear_journal(project: Path) -> None:
    safe_path(project, JOURNAL_FILE).unlink(missing_ok=True)


def _recover_interrupted_commit(project: Path, state: dict) -> None:
    """Resolve a commit that was interrupted by a crash or kill.

    The state file is the commit point: when it already names the journal's
    target the commit finished and only the journal needs cleanup. Otherwise
    roll back to the recorded current revision — restore ``output.html`` from
    its snapshot and drop revision files numbered beyond current.
    """
    current = state.get("revision", 0)
    journal_path = safe_path(project, JOURNAL_FILE)
    journal = None
    if journal_path.is_file():
        try:
            journal = _read_json(journal_path)
        except RevisionError:
            journal = None
    if journal and journal.get("target_revision") == current:
        _clear_journal(project)
        return
    snapshot_path = safe_path(project, f"revisions/rev{current}.html")
    if snapshot_path.is_file():
        # Read the committed bytes, never output.html: it may hold the
        # interrupted attempt's content.
        with snapshot_path.open(encoding="utf-8", newline="") as handle:
            html = handle.read()
        atomic_write(safe_path(project, "output.html"), html)
    for number in available(project, state):
        if number > current:
            for extension in ("html", "json"):
                safe_path(project, f"revisions/rev{number}.{extension}").unlink(missing_ok=True)
    _clear_journal(project)


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
    _write_journal(project, new_number, kind, current)
    try:
        snapshot(project, after, html, kind=kind, parent_revision=current, restored_from=restored_from)
        atomic_write(safe_path(project, "output.html"), html)
        _write_json(safe_path(project, STATE_FILE), after)
    except Exception:
        atomic_write(safe_path(project, "output.html"), old_html)
        _write_json(safe_path(project, STATE_FILE), before)
        for extension in ("html", "json"):
            safe_path(project, f"revisions/rev{new_number}.{extension}").unlink(missing_ok=True)
        _clear_journal(project)
        raise
    _clear_journal(project)
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
