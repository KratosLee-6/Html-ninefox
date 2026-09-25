"""Shared application seam for restoring an Artifact Revision."""

import threading
import time
from pathlib import Path

from htmlninefox import pipeline, revisions
from htmlninefox.application import (
    RestoreError,
    RestoreRequest,
    StudioApplication,
    StudioDependencies,
)


def test_restore_creates_new_revision_through_application_interface(tmp_path: Path) -> None:
    project = pipeline.run_expert(
        "做一个产品介绍落地页",
        output=str(tmp_path),
        quiet_llm=True,
    )["work"]
    original = (project / "output.html").read_bytes()
    pipeline.run_feedback(str(project), "颜色再深一点", allow_llm=False)
    assert (project / "output.html").read_bytes() != original
    studio = StudioApplication(StudioDependencies.for_workspace(tmp_path))

    result = studio.restore(RestoreRequest(
        project=project,
        revision=0,
        expected_revision=1,
    ))

    assert result.project == project.resolve()
    assert result.revision == 2
    assert result.restored_from == 0
    assert (project / "output.html").read_bytes() == original
    assert [item["revision"] for item in revisions.history(project)] == [0, 1, 2]


def test_cli_restore_uses_application_interface(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from htmlninefox.cli import main

    project = pipeline.run_expert(
        "做一个产品介绍落地页",
        output=str(tmp_path),
        quiet_llm=True,
    )["work"]
    original = (project / "output.html").read_bytes()
    pipeline.run_feedback(str(project), "颜色再深一点", allow_llm=False)

    result = CliRunner().invoke(main, [
        "restore",
        "--project", str(project),
        "--revision", "0",
        "--expected-revision", "1",
    ])

    assert result.exit_code == 0, result.output
    assert "rev2" in result.output
    assert (project / "output.html").read_bytes() == original


def test_restore_conflict_has_stable_error(tmp_path: Path) -> None:
    from htmlninefox.application import RestoreError

    project = pipeline.run_expert(
        "做一个产品介绍落地页",
        output=str(tmp_path),
        quiet_llm=True,
    )["work"]
    pipeline.run_feedback(str(project), "颜色再深一点", allow_llm=False)
    studio = StudioApplication(StudioDependencies.for_workspace(tmp_path))
    studio.restore(RestoreRequest(
        project=project,
        revision=0,
        expected_revision=1,
    ))

    try:
        studio.restore(RestoreRequest(
            project=project,
            revision=0,
            expected_revision=1,
        ))
    except RestoreError as error:
        captured = error
    else:
        raise AssertionError("conflicting Restore unexpectedly succeeded")

    assert captured.code == "revision_conflict"
    assert captured.message == "项目已有新版本，请刷新版本列表后重试"


def test_restore_serializes_concurrent_calls_for_one_project(tmp_path: Path) -> None:
    project = pipeline.run_expert(
        "做一个产品介绍落地页",
        output=str(tmp_path),
        quiet_llm=True,
    )["work"]
    original = (project / "output.html").read_bytes()
    pipeline.run_feedback(str(project), "颜色再深一点", allow_llm=False)

    entered = threading.Event()
    release = threading.Event()
    entries: list[int] = []

    def gated_restore(path, revision, expected_revision):
        entries.append(expected_revision)
        entered.set()
        release.wait(timeout=10)
        return revisions.restore(path, revision, expected_revision)

    studio = StudioApplication(StudioDependencies.for_workspace(
        tmp_path, restore_revision=gated_restore,
    ))
    request = RestoreRequest(project=project, revision=0, expected_revision=1)
    first: dict[str, object] = {}
    second: dict[str, object] = {}

    def run(outcome: dict[str, object]) -> None:
        try:
            studio.restore(request)
            outcome["code"] = "ok"
        except RestoreError as error:
            outcome["code"] = error.code

    first_thread = threading.Thread(target=run, args=(first,))
    first_thread.start()
    assert entered.wait(timeout=10), "first Restore never reached the seam"
    second_thread = threading.Thread(target=run, args=(second,))
    second_thread.start()
    time.sleep(0.3)
    assert len(entries) == 1, "second Restore entered the seam before the first finished"
    assert "code" not in second, "second Restore finished while the first still held the lock"

    release.set()
    first_thread.join(timeout=10)
    second_thread.join(timeout=10)
    assert first.get("code") == "ok"
    assert second.get("code") == "revision_conflict"
    assert (project / "output.html").read_bytes() == original
    assert [item["revision"] for item in revisions.history(project)] == [0, 1, 2]
