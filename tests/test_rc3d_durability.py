"""RC3-D: crash-recoverable Project commits, durable writes, process locking."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from htmlninefox import durable, pipeline, revisions
from htmlninefox.server.storage import ProjectStore
from test_server_project_api import request as api_request

REPO_ROOT = Path(__file__).resolve().parent.parent


def revisioned_project(tmp_path: Path) -> tuple[Path, str]:
    """A project at rev1 plus the committed rev1 HTML bytes."""
    work = pipeline.run_expert(
        "做一个产品介绍落地页", output=str(tmp_path), quiet_llm=True)["work"]
    pipeline.run_feedback(str(work), "颜色再深一点", allow_llm=False)
    committed = _read_exact(work / "revisions" / "rev1.html")
    return work, committed


def _read_exact(path: Path) -> str:
    """Read text without newline translation; Path.read_text gained
    newline= only in Python 3.13 and CI runs 3.12."""
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def _simulate_interrupted_commit(work: Path, *, replace_output: bool) -> str:
    attempt = "<html><body>interrupted attempt</body></html>"
    revisions.snapshot(
        work, {"revision": 2}, attempt, kind="feedback", parent_revision=1)
    if replace_output:
        revisions.atomic_write(work / "output.html", attempt)
    revisions._write_json(work / revisions.JOURNAL_FILE, {
        "schema_version": 1,
        "target_revision": 2,
        "parent_revision": 1,
        "kind": "feedback",
        "created_at": "2026-09-25T00:00:00",
    })
    return attempt


def test_interrupted_after_snapshot_rolls_back_on_next_load(tmp_path: Path) -> None:
    work, committed = revisioned_project(tmp_path)
    _simulate_interrupted_commit(work, replace_output=False)

    state = revisions.load_state(work)

    assert state["revision"] == 1
    assert not (work / "revisions" / "rev2.html").exists()
    assert not (work / "revisions" / "rev2.json").exists()
    assert not (work / revisions.JOURNAL_FILE).exists()
    assert _read_exact(work / "output.html") == committed
    assert [item["revision"] for item in revisions.history(work)] == [0, 1]


def test_interrupted_after_output_rolls_back_on_next_load(tmp_path: Path) -> None:
    work, committed = revisioned_project(tmp_path)
    _simulate_interrupted_commit(work, replace_output=True)
    assert (work / "output.html").read_text(encoding="utf-8") != committed

    state = revisions.load_state(work)

    assert state["revision"] == 1
    assert _read_exact(work / "output.html") == committed
    assert not (work / revisions.JOURNAL_FILE).exists()
    assert [item["revision"] for item in revisions.history(work)] == [0, 1]


def test_completed_commit_only_cleans_the_journal(tmp_path: Path) -> None:
    work, _ = revisioned_project(tmp_path)
    pipeline.run_feedback(str(work), "标题再大一点", allow_llm=False)  # rev2 committed
    after_output = (work / "output.html").read_bytes()
    revisions._write_json(work / revisions.JOURNAL_FILE, {
        "schema_version": 1,
        "target_revision": 2,
        "parent_revision": 1,
        "kind": "feedback",
        "created_at": "2026-09-25T00:00:00",
    })

    state = revisions.load_state(work)

    assert state["revision"] == 2
    assert not (work / revisions.JOURNAL_FILE).exists()
    assert (work / "output.html").read_bytes() == after_output
    assert [item["revision"] for item in revisions.history(work)] == [0, 1, 2]


def test_corrupt_journal_still_rolls_back_by_revision_number(tmp_path: Path) -> None:
    work, committed = revisioned_project(tmp_path)
    _simulate_interrupted_commit(work, replace_output=True)
    (work / revisions.JOURNAL_FILE).write_text("{broken", encoding="utf-8")

    state = revisions.load_state(work)

    assert state["revision"] == 1
    assert _read_exact(work / "output.html") == committed
    assert not (work / revisions.JOURNAL_FILE).exists()


def test_failed_commit_leaves_no_journal(tmp_path: Path, monkeypatch) -> None:
    work = pipeline.run_expert(
        "做一个产品介绍落地页", output=str(tmp_path), quiet_llm=True)["work"]
    original = revisions.atomic_write
    calls = {"count": 0}

    def fail_once(path, body):
        if path.name == revisions.STATE_FILE and path.parent == work:
            calls["count"] += 1
            if calls["count"] == 1:
                raise OSError("disk unavailable")
        return original(path, body)

    state = revisions.load_state(work)
    before = dict(state)
    monkeypatch.setattr(revisions, "atomic_write", fail_once)
    with pytest.raises(OSError):
        revisions.commit(work, before, dict(state, preset=dict(state.get("preset") or {})),
                         "<html><body>next</body></html>", kind="feedback")

    assert not (work / revisions.JOURNAL_FILE).exists()
    assert revisions.load_state(work)["revision"] == 0


def test_cross_process_file_lock_blocks_and_releases(tmp_path: Path) -> None:
    project = tmp_path / "project"
    lock_path = revisions.lock_file(project)
    child_code = (
        "import sys, time\n"
        "from htmlninefox import durable\n"
        "handle = durable.acquire_file_lock(durable.Path(sys.argv[1]), timeout=5)\n"
        "print('LOCKED', flush=True)\n"
        "time.sleep(float(sys.argv[2]))\n"
        "durable.release_file_lock(handle)\n"
    )
    child = subprocess.Popen(
        [sys.executable, "-c", child_code, str(lock_path), "2"],
        cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8",
    )
    try:
        assert child.stdout is not None
        assert child.stdout.readline().strip() == "LOCKED"
        with pytest.raises(durable.LockBusyError):
            durable.acquire_file_lock(lock_path, timeout=0.4)
    finally:
        assert child.wait(timeout=10) == 0

    handle = durable.acquire_file_lock(lock_path, timeout=2)
    durable.release_file_lock(handle)


def test_project_lock_is_reentrant_in_one_thread(tmp_path: Path) -> None:
    with revisions.project_lock(tmp_path):
        with revisions.project_lock(tmp_path):
            with revisions.project_lock(tmp_path):
                pass
    assert not revisions._lock_handles
    with revisions.project_lock(tmp_path):
        pass
    assert not revisions._lock_handles


def test_http_restore_reports_busy_while_external_lock_is_held(
        tmp_path: Path, workbench_server, monkeypatch) -> None:
    with workbench_server as server:
        base, root = server.base_url, server.output_root
        work = pipeline.run_expert(
            "做一个产品介绍落地页", output=str(root), quiet_llm=True)["work"]
        pipeline.run_feedback(str(work), "颜色再深一点", allow_llm=False)
        name = work.name
        path = f"/api/projects/{name}/restore-revision"
        payload = {"revision": 0, "expected_revision": 1}

        monkeypatch.setattr(revisions, "LOCK_TIMEOUT_SECONDS", 0.4)
        handle = durable.acquire_file_lock(revisions.lock_file(work), timeout=2)
        try:
            busy, _ = api_request(base, path, "POST", payload, expected=409)
        finally:
            durable.release_file_lock(handle)
        monkeypatch.setattr(revisions, "LOCK_TIMEOUT_SECONDS", 15.0)

        assert busy["error"]["code"] == "project_busy"

        restored, _ = api_request(base, path, "POST", payload, expected=200)
        assert restored["ok"] is True


def test_failed_generation_leaves_no_partial_project(tmp_path: Path, monkeypatch) -> None:
    from htmlninefox import recipe_run

    def explode(project, run):
        raise OSError("deliver failed")

    monkeypatch.setattr(recipe_run, "write_recipe_run", explode)
    with pytest.raises(OSError):
        pipeline.run_expert(
            "做一个产品介绍落地页", output=str(tmp_path), quiet_llm=True)

    assert not list(tmp_path.glob("html9n-*"))
    assert not list(tmp_path.glob(".gen-*"))


def test_generation_publishes_atomically(tmp_path: Path) -> None:
    result = pipeline.run_expert(
        "做一个产品介绍落地页", output=str(tmp_path), quiet_llm=True)

    work = Path(result["work"])
    assert work.name.startswith("html9n-")
    assert not list(tmp_path.glob(".gen-*"))
    for name in ("output.html", "brief.json", "brief.md", "style.md", "assets.json",
                 pipeline.STATE_FILE, "recipe-run.json"):
        assert (work / name).is_file(), name
    assert (work / "revisions" / "rev0.html").is_file()
    assert (work / "revisions" / "rev0.json").is_file()
    run = json.loads((work / "recipe-run.json").read_text(encoding="utf-8"))
    deliver = next(stage for stage in run["stages"] if stage["id"] == "deliver")
    assert deliver["output_summary"]["project_name"] == work.name


def test_project_store_atomic_json_survives_concurrent_writes(tmp_path: Path) -> None:
    target = tmp_path / "shared" / "state.json"
    errors: list[Exception] = []

    def churn(tag: str) -> None:
        try:
            for index in range(40):
                ProjectStore._atomic_json(target, {"tag": tag, "index": index})
        except Exception as error:  # noqa: BLE001
            errors.append(error)

    threads = [threading.Thread(target=churn, args=(tag,)) for tag in ("a", "b", "c")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert not errors
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert isinstance(payload["index"], int)
    assert not list(target.parent.glob("*.tmp"))
    assert not list(target.parent.glob(".revision-*"))


def test_twenty_revision_churn_stays_consistent(tmp_path: Path) -> None:
    work = pipeline.run_expert(
        "做一个产品介绍落地页", output=str(tmp_path), quiet_llm=True)["work"]
    for _ in range(20):
        pipeline.run_feedback(str(work), "颜色再深一点", allow_llm=False)
        assert not (work / revisions.JOURNAL_FILE).exists()

    state = revisions.load_state(work)
    assert state["revision"] == 20
    assert [item["revision"] for item in revisions.history(work)] == list(range(21))
