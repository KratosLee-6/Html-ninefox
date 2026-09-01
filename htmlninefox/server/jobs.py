"""Persistent asynchronous jobs for long-running local generation tasks."""

from __future__ import annotations

import json
import os
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .storage import StoreError

_ACTIVE = {"queued", "running"}
_REGISTRY: dict[Path, "JobManager"] = {}
_REGISTRY_LOCK = threading.Lock()


def get_job_manager(root: str | Path) -> "JobManager":
    resolved = Path(root).expanduser().resolve()
    with _REGISTRY_LOCK:
        manager = _REGISTRY.get(resolved)
        if manager is None:
            manager = JobManager(resolved)
            _REGISTRY[resolved] = manager
        return manager


class JobManager:
    def __init__(self, root: str | Path, max_workers: int = 2):
        self.root = Path(root).expanduser().resolve()
        self.job_dir = self.root / ".jobs"
        self.job_dir.mkdir(parents=True, exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="htmlninefox-job")
        self.lock = threading.RLock()
        self.futures: dict[str, Future] = {}
        self._recover_interrupted_jobs()

    def submit(self, kind: str, run: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        job_id = uuid.uuid4().hex[:16]
        now = self._now()
        state = {
            "id": job_id,
            "kind": kind,
            "status": "queued",
            "progress": 0,
            "stage": "queued",
            "created_at": now,
            "updated_at": now,
            "result": None,
            "error": None,
        }
        with self.lock:
            self._write(state)
            self.futures[job_id] = self.executor.submit(self._execute, job_id, run)
        return state

    def get(self, job_id: str) -> dict[str, Any]:
        self._validate_id(job_id)
        path = self._path(job_id)
        if not path.is_file():
            raise StoreError("job_not_found", f"任务不存在：{job_id}", 404)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise StoreError("job_state_invalid", f"任务状态损坏：{job_id}", 409) from exc

    def list(self, limit: int = 30) -> list[dict[str, Any]]:
        states = []
        for path in sorted(self.job_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                states.append(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                continue
            if len(states) >= limit:
                break
        return states

    def cancel(self, job_id: str) -> dict[str, Any]:
        with self.lock:
            state = self.get(job_id)
            if state["status"] not in _ACTIVE:
                raise StoreError("job_not_cancellable", "任务已经结束，无法取消", 409,
                                 {"status": state["status"]})
            future = self.futures.get(job_id)
            if state["status"] == "running" or future is None or not future.cancel():
                raise StoreError("job_not_cancellable", "任务已经开始执行，当前版本无法安全中断", 409,
                                 {"status": state["status"]})
            state.update({"status": "cancelled", "stage": "cancelled", "updated_at": self._now()})
            self._write(state)
            return state

    def _execute(self, job_id: str, run: Callable[[], dict[str, Any]]) -> None:
        with self.lock:
            state = self.get(job_id)
            if state["status"] == "cancelled":
                return
            state.update({"status": "running", "progress": 10, "stage": "generating",
                          "started_at": self._now(), "updated_at": self._now()})
            self._write(state)
        try:
            result = run()
        except StoreError as error:
            self._finish_failed(job_id, error.code, error.message, error.details)
        except Exception as error:  # noqa: BLE001
            self._finish_failed(job_id, "job_failed", str(error) or error.__class__.__name__, {})
        else:
            with self.lock:
                state = self.get(job_id)
                state.update({"status": "succeeded", "progress": 100, "stage": "completed",
                              "result": result, "error": None, "finished_at": self._now(),
                              "updated_at": self._now()})
                self._write(state)

    def _finish_failed(self, job_id: str, code: str, message: str, details: dict[str, Any]) -> None:
        with self.lock:
            state = self.get(job_id)
            state.update({"status": "failed", "stage": "failed", "error": {
                "code": code, "message": message, "details": details,
            }, "finished_at": self._now(), "updated_at": self._now()})
            self._write(state)

    def _recover_interrupted_jobs(self) -> None:
        for path in self.job_dir.glob("*.json"):
            try:
                state = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if state.get("status") in _ACTIVE:
                state.update({"status": "failed", "stage": "interrupted", "error": {
                    "code": "job_interrupted", "message": "服务重启时任务尚未完成", "details": {},
                }, "finished_at": self._now(), "updated_at": self._now()})
                self._write(state)

    def _path(self, job_id: str) -> Path:
        return self.job_dir / f"{job_id}.json"

    @staticmethod
    def _validate_id(job_id: str) -> None:
        if len(job_id) != 16 or any(char not in "0123456789abcdef" for char in job_id):
            raise StoreError("job_id_invalid", "任务 ID 不合法", 400)

    def _write(self, state: dict[str, Any]) -> None:
        path = self._path(state["id"])
        temp = path.with_suffix(".json.tmp")
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="milliseconds")
