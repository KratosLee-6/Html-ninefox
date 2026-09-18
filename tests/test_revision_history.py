"""Artifact history must preserve both output and editable generation state."""

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from htmlninefox import pipeline, revisions


def generated(tmp_path):
    return pipeline.run_expert("做一个产品落地页", output=str(tmp_path), quiet_llm=True)["work"]


def test_restore_then_feedback_uses_restored_preset_and_preserves_history(tmp_path):
    project = generated(tmp_path)
    original = revisions.load_state(project)
    original_html = (project / "output.html").read_bytes()
    first = pipeline.run_feedback(str(project), "颜色再深一点", allow_llm=False)
    assert first["ok"] and first["revision"] == 1
    changed_html = (project / "output.html").read_bytes()
    assert changed_html != original_html
    revisions.name_revision(project, 0, "客户确认稿")
    restored = revisions.restore(project, 0, expected_revision=1)
    assert restored["revision"] == 2
    assert restored["preset"] == original["preset"]
    assert (project / "output.html").read_bytes() == original_html
    assert (project / "revisions/rev1.html").read_bytes() == changed_html
    assert revisions.history(project)[0]["label"] == "客户确认稿"
    record = revisions.history(project)[-1]
    assert (record["parent_revision"], record["restored_from"]) == (1, 0)
    updated = pipeline.run_feedback(str(project), "字体大一点", allow_llm=False)
    assert updated["revision"] == 3
    assert revisions.load_state(project)["preset"]["tokens"]["primary"] == original["preset"]["tokens"]["primary"]
    assert [item["revision"] for item in revisions.history(project)] == [0, 1, 2, 3]


def test_generation_rerun_is_versioned_and_failed_render_does_not_replace_output(tmp_path, monkeypatch):
    project = generated(tmp_path)
    original = (project / "output.html").read_bytes()
    result = pipeline.rerun_project(project, "generate")
    assert result["revision"] == 1
    assert revisions.history(project)[-1]["kind"] == "rerun"
    pipeline.rerun_project(project, "verify")
    assert len(revisions.history(project)) == 2
    before = revisions.load_state(project)
    monkeypatch.setattr(pipeline, "_render_state", lambda *_: "invalid html")
    with pytest.raises(ValueError, match="质量"):
        pipeline.rerun_project(project, "generate")
    assert revisions.load_state(project) == before
    assert (project / "revisions/rev0.html").read_bytes() == original
    assert (project / "output.html").read_bytes() == (project / "revisions/rev1.html").read_bytes()


def test_concurrent_restore_has_one_winner(tmp_path):
    project = generated(tmp_path)
    pipeline.rerun_project(project, "generate")

    def restore():
        try:
            return revisions.restore(project, 0, 1)["revision"]
        except revisions.RevisionError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: restore(), range(2)))
    assert set(results) == {2, "revision_conflict"}
    assert len(revisions.history(project)) == 3


def test_failed_state_write_preserves_current_output_and_history(tmp_path, monkeypatch):
    project = generated(tmp_path)
    pipeline.run_feedback(str(project), "颜色再深一点", allow_llm=False)
    before = revisions.load_state(project)
    html = (project / "output.html").read_bytes()
    write = revisions.atomic_write
    failed = False

    def fail_once(path, body):
        nonlocal failed
        if path.name == pipeline.STATE_FILE and not failed:
            failed = True
            raise OSError("disk unavailable")
        return write(path, body)

    monkeypatch.setattr(revisions, "atomic_write", fail_once)
    with pytest.raises(OSError, match="disk unavailable"):
        revisions.restore(project, 0, 1)
    assert revisions.load_state(project) == before
    assert (project / "output.html").read_bytes() == html
    assert len(revisions.history(project)) == 2
    assert not (project / "revisions/rev2.json").exists()


def test_legacy_history_is_readable_and_current_state_is_checkpointed(tmp_path):
    project = generated(tmp_path)
    (project / "revisions/rev0.json").unlink()
    pipeline.rerun_project(project, "generate")
    # The first new edit preserves the old current state for future restoration.
    assert revisions.history(project)[0]["can_restore"]
    (project / "revisions/rev0.json").unlink()
    revisions.name_revision(project, 0, "早期稿")
    assert not revisions.history(project)[0]["can_restore"]
    with pytest.raises(revisions.RevisionError, match="缺少生成配置"):
        revisions.restore(project, 0, 1)
    assert revisions.load_state(project)["revision"] == 1


@pytest.mark.parametrize("value", [[], {"revision": "bad"}, {"revision": -1}, {"revision": True}])
def test_corrupt_state_has_explicit_error(tmp_path, value):
    (tmp_path / pipeline.STATE_FILE).write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(revisions.RevisionError) as error:
        revisions.load_state(tmp_path)
    assert error.value.code == "project_state_invalid"


def test_restore_preserves_crlf_bytes(tmp_path):
    project = generated(tmp_path)
    state = revisions.load_state(project)
    html = "<!doctype html>\r\n<html><body>原稿</body></html>\r\n"
    revisions.atomic_write(project / "output.html", html)
    revisions.snapshot(project, state, html)
    pipeline.rerun_project(project, "generate")
    revisions.restore(project, 0, 1)
    assert (project / "output.html").read_bytes() == html.encode("utf-8")


def test_external_revision_symlink_is_rejected(tmp_path):
    project = generated(tmp_path)
    pipeline.rerun_project(project, "generate")
    outside = tmp_path / "outside.html"
    outside.write_text("private", encoding="utf-8")
    snapshot = project / "revisions/rev0.html"
    snapshot.unlink()
    try:
        snapshot.symlink_to(outside)
    except OSError:
        pytest.skip("Host does not permit symlinks")
    with pytest.raises(revisions.RevisionError) as error:
        revisions.restore(project, 0, 1)
    assert error.value.code == "revision_forbidden"
