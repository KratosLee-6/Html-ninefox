"""Observable Recipe Run state shared by generation jobs and project reruns."""

from __future__ import annotations

import copy
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from . import revisions

RECIPE_RUN_FILE = "recipe-run.json"
SCHEMA_VERSION = 1
STAGE_DEFINITIONS = (
    ("analyze", "需求分析", "Analyze", 8, 22, False),
    ("compose", "组合配方", "Compose", 25, 45, False),
    ("generate", "生成产物", "Generate", 48, 72, True),
    ("verify", "质量验证", "Verify", 76, 88, True),
    ("deliver", "保存交付", "Deliver", 92, 98, False),
)

ProgressCallback = Callable[[str, int, dict[str, Any]], None]


def _now() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


class RecipeRunTracker:
    def __init__(self, prompt: str, callback: ProgressCallback | None = None,
                 parent_run_id: str | None = None, rerun_from: str | None = None):
        self.callback = callback
        self._started: dict[str, float] = {}
        self.run: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "id": uuid.uuid4().hex[:16],
            "parent_run_id": parent_run_id,
            "rerun_from": rerun_from,
            "status": "running",
            "prompt_summary": str(prompt or "").strip()[:160],
            "started_at": _now(),
            "finished_at": None,
            "duration_ms": None,
            "stages": [
                {
                    "id": stage_id,
                    "label": label,
                    "label_en": label_en,
                    "status": "pending",
                    "progress_start": progress_start,
                    "progress_end": progress_end,
                    "started_at": None,
                    "finished_at": None,
                    "duration_ms": None,
                    "attempt": 0,
                    "model": None,
                    "fallback_used": None,
                    "input_summary": {},
                    "output_summary": {},
                    "error": None,
                    "rerunnable": rerunnable,
                }
                for stage_id, label, label_en, progress_start, progress_end, rerunnable
                in STAGE_DEFINITIONS
            ],
        }
        self._run_started = time.perf_counter()

    def stage(self, stage_id: str) -> dict[str, Any]:
        for stage in self.run["stages"]:
            if stage["id"] == stage_id:
                return stage
        raise ValueError(f"unknown recipe stage: {stage_id}")

    def reuse(self, stage_id: str, output_summary: dict[str, Any] | None = None) -> None:
        stage = self.stage(stage_id)
        stage.update({
            "status": "reused",
            "duration_ms": 0,
            "output_summary": dict(output_summary or {"source": "previous_run"}),
        })

    def start(self, stage_id: str, input_summary: dict[str, Any] | None = None) -> None:
        stage = self.stage(stage_id)
        stage.update({
            "status": "running",
            "started_at": _now(),
            "finished_at": None,
            "duration_ms": None,
            "attempt": int(stage.get("attempt") or 0) + 1,
            "input_summary": dict(input_summary or {}),
            "output_summary": {},
            "error": None,
        })
        self._started[stage_id] = time.perf_counter()
        self._emit(stage_id, int(stage["progress_start"]))

    def complete(self, stage_id: str, output_summary: dict[str, Any] | None = None,
                 model: str | None = None, fallback_used: bool | None = None) -> None:
        stage = self.stage(stage_id)
        started = self._started.pop(stage_id, time.perf_counter())
        stage.update({
            "status": "succeeded",
            "finished_at": _now(),
            "duration_ms": max(0, round((time.perf_counter() - started) * 1000)),
            "output_summary": dict(output_summary or {}),
            "model": model,
            "fallback_used": fallback_used,
        })
        self._emit(stage_id, int(stage["progress_end"]))

    def fail(self, stage_id: str, error: Exception) -> None:
        stage = self.stage(stage_id)
        started = self._started.pop(stage_id, time.perf_counter())
        stage.update({
            "status": "failed",
            "finished_at": _now(),
            "duration_ms": max(0, round((time.perf_counter() - started) * 1000)),
            "error": {
                "type": error.__class__.__name__,
                "message": str(error) or error.__class__.__name__,
            },
        })
        self.run.update({
            "status": "failed",
            "finished_at": _now(),
            "duration_ms": max(0, round((time.perf_counter() - self._run_started) * 1000)),
        })
        self._emit(stage_id, int(stage["progress_end"]))

    def succeed(self) -> dict[str, Any]:
        self.run.update({
            "status": "succeeded",
            "finished_at": _now(),
            "duration_ms": max(0, round((time.perf_counter() - self._run_started) * 1000)),
        })
        self._emit("completed", 100)
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self.run)

    def _emit(self, stage_id: str, progress: int) -> None:
        if self.callback:
            self.callback(stage_id, progress, self.snapshot())


def verify_html(html: str) -> dict[str, Any]:
    source = str(html or "")
    lowered = source.lower()
    checks = {
        "non_empty": len(source.strip()) >= 200,
        "doctype": "<!doctype html" in lowered,
        "html_element": "<html" in lowered and "</html>" in lowered,
        "body_element": "<body" in lowered and "</body>" in lowered,
        "viewport": "name=\"viewport\"" in lowered or "name='viewport'" in lowered,
    }
    required = checks["non_empty"] and checks["doctype"]
    score = round(sum(1 for value in checks.values() if value) / len(checks) * 100)
    warnings = [name for name, passed in checks.items() if not passed]
    return {
        "ok": required,
        "score": score,
        "html_bytes": len(source.encode("utf-8")),
        "checks": checks,
        "warnings": warnings,
    }


def write_recipe_run(project: str | Path, run: dict[str, Any]) -> Path:
    target = Path(project) / RECIPE_RUN_FILE
    revisions.atomic_write(target, json.dumps(run, ensure_ascii=False, indent=2))
    return target