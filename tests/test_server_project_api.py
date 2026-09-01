"""HTTP v1 project CRUD, workspace recovery, and error contract."""

from __future__ import annotations

import base64
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from htmlninefox import pipeline
from htmlninefox.server import app as server_app


def make_project(root: Path, name: str = "alpha") -> Path:
    project = root / name
    project.mkdir()
    (project / "output.html").write_text("<!doctype html><title>project</title>", encoding="utf-8")
    (project / pipeline.STATE_FILE).write_text(json.dumps({
        "prompt": "API 项目",
        "intent": "landing",
        "preset_id": "linear-light",
        "revision": 0,
        "created_at": "2026-08-31T12:00:00",
    }, ensure_ascii=False), encoding="utf-8")
    return project


@pytest.fixture()
def api_server(tmp_path):
    server_app._OUTPUT_ROOT = tmp_path
    server = server_app.ThreadingHTTPServer(("127.0.0.1", 0), server_app._Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield base, tmp_path
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def request(base: str, path: str, method: str = "GET", data: dict | None = None,
            expected: int = 200) -> tuple[dict, urllib.response.addinfourl | urllib.error.HTTPError]:
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(base + path, data=body, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        response = urllib.request.urlopen(req, timeout=10)
        assert response.status == expected
        return json.loads(response.read().decode("utf-8")), response
    except urllib.error.HTTPError as error:
        payload = json.loads(error.read().decode("utf-8"))
        assert error.code == expected, payload
        return payload, error


def test_project_crud_http(api_server):
    base, root = api_server
    make_project(root)

    projects, _ = request(base, "/api/projects")
    assert projects["items"][0]["name"] == "alpha"

    renamed, _ = request(base, "/api/projects/alpha", "PATCH", {"new_name": "beta"})
    assert renamed["project"]["name"] == "beta"

    copied, _ = request(base, "/api/projects/beta/duplicate", "POST", {}, expected=201)
    assert copied["project"]["name"] == "beta-copy"

    deleted, _ = request(base, "/api/projects/beta", "DELETE")
    assert deleted["recoverable"] is True
    assert (root / ".trash").is_dir()


def test_workspace_http_roundtrip_and_recovery(api_server):
    base, root = api_server
    first = {"schema_version": 1, "canvas": {
        "camera": {"x": 0, "y": 0, "z": 1}, "nodes": [{"id": 1}], "edges": [], "uid": 2, "wsSeq": 1}}
    saved, _ = request(base, "/api/workspace", "PUT", first)
    assert saved["saved"] is True

    loaded, _ = request(base, "/api/workspace")
    assert loaded["state"]["canvas"]["nodes"] == [{"id": 1}]

    second = json.loads(json.dumps(first))
    second["canvas"]["nodes"] = [{"id": 2}]
    request(base, "/api/workspace", "PUT", second)
    (root / ".workspace.json").write_text("broken", encoding="utf-8")
    recovered, _ = request(base, "/api/workspace")
    assert recovered["recovered"] is True
    assert recovered["state"]["canvas"]["nodes"] == [{"id": 1}]


def test_error_contract_has_code_message_and_request_id(api_server):
    base, _ = api_server
    payload, response = request(base, "/api/projects/missing", expected=404)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "project_not_found"
    assert payload["error"]["message"]
    assert payload["request_id"] == response.headers["X-Request-ID"]

    invalid, _ = request(base, "/api/workspace", "PUT", {"schema_version": 99}, expected=409)
    assert invalid["error"]["code"] == "workspace_schema_unsupported"


def test_template_preview_http(api_server):
    base, _ = api_server
    response = urllib.request.urlopen(
        base + "/api/template-preview?intent=dashboard&template=vercel-dark", timeout=10)
    html = response.read().decode("utf-8")
    assert response.headers["Content-Type"].startswith("text/html")
    assert "<!doctype html>" in html.lower()
    assert "--fox-bg" in html

    invalid, _ = request(base, "/api/template-preview?intent=missing", expected=400)
    assert invalid["error"]["code"] == "template_preview_invalid"


def test_generate_job_and_diagnostic_download(api_server):
    base, root = api_server
    submitted, _ = request(base, "/api/jobs", "POST", {
        "prompt": "做一个深色 SaaS 落地页", "intent": "landing", "quiet_llm": True,
    }, expected=202)
    job_id = submitted["job"]["id"]
    deadline = time.time() + 15
    job = None
    while time.time() < deadline:
        job, _ = request(base, f"/api/jobs/{job_id}")
        if job["status"] in {"succeeded", "failed"}:
            break
        time.sleep(0.1)
    assert job and job["status"] == "succeeded", job
    assert (root / job["result"]["project_name"] / "output.html").is_file()
    assert not (root / ".jobs-work").exists() or not any((root / ".jobs-work").iterdir())

    diagnostic, _ = request(base, "/api/diagnostics", "POST", {}, expected=201)
    download = urllib.request.urlopen(base + diagnostic["bundle"]["download_url"], timeout=10)
    assert download.headers["Content-Type"] == "application/zip"
    assert download.read(2) == b"PK"


def test_gallery_api_returns_real_html_and_page_preview(api_server):
    base, _ = api_server
    gallery, _ = request(base, "/api/gallery")
    assert len(gallery["items"]) >= 6
    item = next(entry for entry in gallery["items"] if entry["id"] == "guizang-editorial-ink")
    assert len(item["pages"]) >= 5

    with urllib.request.urlopen(base + item["preview_url"], timeout=10) as response:
        full_html = response.read().decode("utf-8")
    assert "data-page=\"cover\"" in full_html
    assert "归藏" in full_html

    page_url = item["pages"][0]["preview_url"]
    with urllib.request.urlopen(base + page_url, timeout=10) as response:
        page_html = response.read().decode("utf-8")
    assert '.page[data-page="cover"]' in page_html
    assert ".nav,.counter{display:none" in page_html


def test_ai_settings_are_local_and_secret_safe(api_server):
    base, root = api_server
    saved, _ = request(base, "/api/settings/ai", "PUT", {
        "enabled": True,
        "provider": "openai-compatible",
        "model": "demo-model",
        "base_url": "http://127.0.0.1:9999/v1",
        "api_key": "secret-value",
    })
    assert saved["settings"]["api_key_set"] is True
    assert "secret-value" not in json.dumps(saved)

    loaded, _ = request(base, "/api/settings/ai")
    assert loaded["settings"]["model"] == "demo-model"
    assert "api_key" not in loaded["settings"]
    stored = json.loads((root / ".settings" / "ai.json").read_text(encoding="utf-8"))
    assert stored["api_key"] == "secret-value"


def test_input_upload_feeds_analysis_and_recommendation(api_server):
    base, _ = api_server
    uploaded, _ = request(base, "/api/inputs", "POST", {
        "name": "requirements.md",
        "mime": "text/markdown",
        "data_base64": base64.b64encode("做一份 AI 产品发布会 PPT".encode()).decode(),
    }, expected=201)
    input_id = uploaded["input"]["id"]
    analyzed, _ = request(base, "/api/analyze", "POST", {
        "prompt": "突出模板预览和自由组合",
        "inputs": [input_id],
    })
    assert analyzed["inputs"][0]["name"] == "requirements.md"
    assert analyzed["recommended_template"]["preview_url"].startswith("/api/gallery-preview")
    assert analyzed["recommended_blocks"]
