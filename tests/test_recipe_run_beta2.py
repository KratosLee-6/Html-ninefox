"""Regression coverage for v0.5 Beta 2 Recipe Run observability."""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from pathlib import Path

from htmlninefox import pipeline
from htmlninefox.server.jobs import JobManager


def wait_job(manager: JobManager, job_id: str, timeout: float = 5) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = manager.get(job_id)
        if state["status"] in {"succeeded", "failed"}:
            return state
        time.sleep(0.02)
    raise AssertionError(f"job did not finish: {job_id}")


def request(base: str, path: str, method: str = "GET", body: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        base + path, data=data, method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))


def poll_api_job(base: str, job_id: str, timeout: float = 20) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = request(base, f"/api/jobs/{job_id}")
        if state["status"] in {"succeeded", "failed"}:
            return state
        time.sleep(0.05)
    raise AssertionError(f"API job did not finish: {job_id}")


def test_pipeline_persists_five_stage_recipe_and_supports_verify_rerun(tmp_path):
    events = []
    result = pipeline.run_expert(
        "做一个像素花园产品介绍页",
        output=str(tmp_path),
        quiet_llm=True,
        progress_callback=lambda stage, progress, run: events.append(
            (stage, progress, run["status"])),
    )

    recipe = result["recipe_run"]
    assert recipe["status"] == "succeeded"
    assert [stage["id"] for stage in recipe["stages"]] == [
        "analyze", "compose", "generate", "verify", "deliver",
    ]
    assert all(stage["status"] == "succeeded" for stage in recipe["stages"])
    assert all(stage["duration_ms"] >= 0 for stage in recipe["stages"])
    assert recipe["stages"][0]["model"] == "fallback"
    assert result["verification"]["ok"] is True
    assert events[-1] == ("completed", 100, "succeeded")

    saved = json.loads((result["work"] / "recipe-run.json").read_text(encoding="utf-8"))
    assert saved["id"] == recipe["id"]
    state = json.loads((result["work"] / pipeline.STATE_FILE).read_text(encoding="utf-8"))
    assert state["recipe_run"]["id"] == recipe["id"]

    rerun = pipeline.rerun_project(result["work"], "verify")
    assert rerun["recipe_run"]["parent_run_id"] == recipe["id"]
    statuses = {stage["id"]: stage["status"] for stage in rerun["recipe_run"]["stages"]}
    assert statuses == {
        "analyze": "reused", "compose": "reused", "generate": "reused",
        "verify": "succeeded", "deliver": "succeeded",
    }


def test_job_manager_persists_live_recipe_progress(tmp_path):
    manager = JobManager(tmp_path, max_workers=1)
    release = threading.Event()
    recipe = {"id": "recipe123", "status": "running", "stages": []}

    def run(report):
        report("compose", 45, recipe)
        release.wait(2)
        return {"ok": True, "recipe_run": {**recipe, "status": "succeeded"}}

    job = manager.submit("generate", run, with_reporter=True)
    deadline = time.time() + 2
    live = None
    while time.time() < deadline:
        live = manager.get(job["id"])
        if live["stage"] == "compose":
            break
        time.sleep(0.02)
    assert live and live["progress"] == 45
    assert live["recipe_run"]["id"] == "recipe123"
    release.set()
    finished = wait_job(manager, job["id"])
    assert finished["recipe_run"]["status"] == "succeeded"
    manager.executor.shutdown(wait=True)


def test_generation_job_and_recipe_rerun_api(workbench_server):
    with workbench_server as server:
        base = server.base_url
        submitted = request(base, "/api/jobs", "POST", {
            "prompt": "做一个本地优先的 HTML 工具介绍页",
            "intent": "landing",
            "quiet_llm": True,
        })
        generated = poll_api_job(base, submitted["job"]["id"])
        assert generated["status"] == "succeeded", generated.get("error")
        result = generated["result"]
        assert generated["recipe_run"]["status"] == "succeeded"
        assert result["verification"]["score"] >= 80

        rerun_submission = request(
            base,
            f"/api/projects/{result['project_name']}/recipe-rerun",
            "POST",
            {"stage": "verify"},
        )
        rerun = poll_api_job(base, rerun_submission["job"]["id"])
        assert rerun["status"] == "succeeded", rerun.get("error")
        assert rerun["result"]["rerun_from"] == "verify"
        assert rerun["result"]["recipe_run"]["parent_run_id"] == result["recipe_run"]["id"]
