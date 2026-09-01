"""ProjectStore filesystem behavior and Canvas Schema v1 recovery."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from htmlninefox import pipeline
from htmlninefox.server.storage import ProjectStore, StoreError


def make_project(root: Path, name: str = "demo") -> Path:
    project = root / name
    project.mkdir()
    (project / "output.html").write_text("<!doctype html><title>demo</title>", encoding="utf-8")
    (project / pipeline.STATE_FILE).write_text(json.dumps({
        "prompt": "做一个测试项目",
        "intent": "landing",
        "preset_id": "linear-light",
        "revision": 2,
        "created_at": "2026-08-31T12:00:00",
    }, ensure_ascii=False), encoding="utf-8")
    return project


def canvas_payload(node_title: str = "需求") -> dict:
    return {
        "schema_version": 1,
        "canvas": {
            "camera": {"x": 1, "y": 2, "z": 1},
            "nodes": [{"id": 1, "kind": "requirement", "data": {"title": node_title}}],
            "edges": [],
            "uid": 2,
            "wsSeq": 1,
        },
    }


def test_project_crud_and_soft_delete(tmp_path):
    make_project(tmp_path, "alpha")
    store = ProjectStore(tmp_path)

    listed = store.list_projects()
    assert listed[0]["name"] == "alpha"
    assert listed[0]["revision"] == 2

    renamed = store.rename_project("alpha", "beta")
    assert renamed["name"] == "beta"
    assert not (tmp_path / "alpha").exists()

    duplicated = store.duplicate_project("beta")
    assert duplicated["name"] == "beta-copy"
    duplicate_state = json.loads((tmp_path / "beta-copy" / pipeline.STATE_FILE).read_text(encoding="utf-8"))
    assert duplicate_state["duplicated_from"] == "beta"

    deleted = store.delete_project("beta")
    assert deleted == {"name": "beta", "deleted": True, "recoverable": True}
    assert not (tmp_path / "beta").exists()
    assert any(path.name.endswith("-beta") for path in (tmp_path / ".trash").iterdir())


def test_project_name_validation_and_conflicts(tmp_path):
    make_project(tmp_path, "alpha")
    make_project(tmp_path, "beta")
    store = ProjectStore(tmp_path)

    with pytest.raises(StoreError) as traversal:
        store.get_project("../alpha")
    assert traversal.value.code == "project_name_invalid"

    with pytest.raises(StoreError) as conflict:
        store.rename_project("alpha", "beta")
    assert conflict.value.status == 409


def test_workspace_save_load_and_backup_recovery(tmp_path):
    store = ProjectStore(tmp_path)
    first = store.save_workspace(canvas_payload("第一版"))
    assert first["schema_version"] == 1

    loaded = store.load_workspace()
    assert loaded["exists"] is True
    assert loaded["recovered"] is False
    assert loaded["state"]["canvas"]["nodes"][0]["data"]["title"] == "第一版"

    store.save_workspace(canvas_payload("第二版"))
    (tmp_path / ".workspace.json").write_text("{broken", encoding="utf-8")
    recovered = store.load_workspace()
    assert recovered["recovered"] is True
    assert recovered["state"]["canvas"]["nodes"][0]["data"]["title"] == "第一版"


def test_workspace_rejects_unknown_schema_and_complexity(tmp_path):
    store = ProjectStore(tmp_path)
    with pytest.raises(StoreError) as schema_error:
        store.save_workspace({"schema_version": 9, "canvas": {}})
    assert schema_error.value.code == "workspace_schema_unsupported"

    payload = canvas_payload()
    payload["canvas"]["nodes"] = [{}] * 501
    with pytest.raises(StoreError) as complexity_error:
        store.save_workspace(payload)
    assert complexity_error.value.status == 413
