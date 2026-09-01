"""Persistent jobs and privacy-conscious diagnostic bundles."""

from __future__ import annotations

import json
import threading
import time
import zipfile
from pathlib import Path

from htmlninefox import pipeline
from htmlninefox.server.diagnostics import create_diagnostic_bundle
from htmlninefox.server.jobs import JobManager
from htmlninefox.server.storage import ProjectStore


def wait_status(manager: JobManager, job_id: str, expected: set[str], timeout: float = 3) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = manager.get(job_id)
        if state["status"] in expected:
            return state
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} did not reach {expected}")


def test_job_succeeds_and_persists_result(tmp_path):
    manager = JobManager(tmp_path, max_workers=1)
    job = manager.submit("demo", lambda: {"project_name": "alpha", "value": 42})
    state = wait_status(manager, job["id"], {"succeeded"})
    assert state["progress"] == 100
    assert state["result"]["value"] == 42
    assert (tmp_path / ".jobs" / f"{job['id']}.json").is_file()
    manager.executor.shutdown(wait=True)


def test_queued_job_can_be_cancelled(tmp_path):
    manager = JobManager(tmp_path, max_workers=1)
    release = threading.Event()
    first = manager.submit("blocker", lambda: (release.wait(2), {"done": True})[1])
    wait_status(manager, first["id"], {"running"})
    second = manager.submit("queued", lambda: {"should_not_run": True})
    cancelled = manager.cancel(second["id"])
    assert cancelled["status"] == "cancelled"
    release.set()
    wait_status(manager, first["id"], {"succeeded"})
    manager.executor.shutdown(wait=True)


def test_job_failure_is_structured(tmp_path):
    manager = JobManager(tmp_path, max_workers=1)

    def fail():
        raise RuntimeError("boom")

    job = manager.submit("demo", fail)
    state = wait_status(manager, job["id"], {"failed"})
    assert state["error"]["code"] == "job_failed"
    assert state["error"]["message"] == "boom"
    manager.executor.shutdown(wait=True)


def test_diagnostic_bundle_excludes_sensitive_content(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")
    project = tmp_path / "alpha"
    project.mkdir()
    (project / "output.html").write_text("SECRET HTML", encoding="utf-8")
    (project / pipeline.STATE_FILE).write_text(json.dumps({
        "prompt": "PRIVATE PROMPT",
        "intent": "landing",
        "preset_id": "linear-light",
        "revision": 1,
    }), encoding="utf-8")
    ProjectStore(tmp_path).save_workspace({"schema_version": 1, "canvas": {
        "camera": {}, "nodes": [{"data": {"text": "PRIVATE CANVAS"}}], "edges": []}})

    bundle = create_diagnostic_bundle(tmp_path, {"api_version": "v1"})
    with zipfile.ZipFile(bundle["path"]) as archive:
        report_text = archive.read("diagnostic.json").decode("utf-8")
        report = json.loads(report_text)
    assert report["configuration"]["environment_keys_present"]["OPENAI_API_KEY"] is True
    assert "secret-value" not in report_text
    assert "PRIVATE PROMPT" not in report_text
    assert "PRIVATE CANVAS" not in report_text
    assert "SECRET HTML" not in report_text
