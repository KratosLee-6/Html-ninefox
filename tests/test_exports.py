"""Export Center analysis, rendering, API, and download coverage."""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from htmlninefox import exporting, pipeline
from htmlninefox.server import app as server_app
from htmlninefox.server.storage import StoreError


def make_project(root: Path, name: str = "export-demo", *, intent: str = "deck") -> Path:
    project = root / name
    project.mkdir()
    project.joinpath("output.html").write_text(
        """<!doctype html><html><head><meta charset="utf-8"><title>导出演示</title>
<style>
html,body{margin:0;width:100%;height:100%;overflow:hidden;font-family:Arial,sans-serif}
.slide{position:absolute;inset:0;width:100vw;height:100vh;display:none;align-items:center;justify-content:center;background:#f7f2df;color:#173c8f;font-size:72px}
.slide.on{display:flex}.slide:nth-child(2){background:#173c8f;color:#f7f2df}
</style></head><body><main class="deck"><section class="slide on">第一页</section><section class="slide">第二页</section></main></body></html>""",
        encoding="utf-8",
    )
    project.joinpath(pipeline.STATE_FILE).write_text(json.dumps({
        "prompt": "导出演示",
        "intent": intent,
        "preset_id": "fox-pixel-garden",
        "revision": 0,
        "created_at": "2026-09-07T09:00:00",
    }, ensure_ascii=False), encoding="utf-8")
    return project


def test_export_analyzer_detects_pages_and_dynamic_risks(tmp_path):
    project = make_project(tmp_path)
    html_path = project / "output.html"
    html_path.write_text(
        html_path.read_text(encoding="utf-8").replace("</body>", "<video src='https://example.com/demo.mp4'></video></body>"),
        encoding="utf-8",
    )
    manifest = exporting.analyze_project(tmp_path, project.name)
    assert manifest["page_model"] == {"selector": ".slide", "count": 2, "paginated": True}
    assert manifest["viewport"] == {"width": 1920, "height": 1080}
    assert "video" in manifest["features"]
    assert manifest["external_assets"] == 1
    assert {item["code"] for item in manifest["warnings"]} == {
        "external_assets", "dynamic_content_flattened",
    }


def test_export_request_parses_page_ranges_and_rejects_invalid_values():
    request = exporting.normalize_export_request({
        "project_name": "alpha", "format": "png", "pages": "1-3,5,3", "scale": 3,
    })
    assert request["pages"] == [1, 2, 3, 5]
    assert request["format"] == "png"
    assert request["scale"] == 3
    with pytest.raises(StoreError) as error:
        exporting.normalize_export_request({"project_name": "alpha", "format": "pptx"})
    assert error.value.code == "export_format_unsupported"


def test_export_project_creates_png_pages_pdf_and_report(tmp_path):
    project = make_project(tmp_path)
    png = exporting.export_project(tmp_path, {
        "project_name": project.name,
        "format": "png",
        "scope": "pages",
        "pages": "1-2",
        "width": 960,
        "height": 540,
        "scale": 1,
    })
    assert [item["name"] for item in png["files"]] == ["page-01.png", "page-02.png"]
    assert all((project / "exports" / png["export_id"] / item["name"]).read_bytes().startswith(b"\x89PNG")
               for item in png["files"])
    report = json.loads((project / "exports" / png["export_id"] / "export-report.json").read_text(encoding="utf-8"))
    assert report["browser"]["page_count"] == 2
    assert report["request"]["pages"] == [1, 2]

    pdf = exporting.export_project(tmp_path, {
        "project_name": project.name,
        "format": "pdf",
        "scope": "pages",
        "pages": [2],
        "width": 960,
        "height": 540,
    })
    pdf_path = project / "exports" / pdf["export_id"] / "document.pdf"
    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert pdf_path.stat().st_size > 1000


def test_export_api_submits_job_and_serves_attachment(tmp_path):
    project = make_project(tmp_path)
    server_app._OUTPUT_ROOT = tmp_path
    server = server_app.ThreadingHTTPServer(("127.0.0.1", 0), server_app._Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        analyze = _json_request(base + "/api/exports/analyze", {
            "project_name": project.name,
        })
        assert analyze["manifest"]["page_model"]["count"] == 2

        submitted = _json_request(base + "/api/exports", {
            "project_name": project.name,
            "format": "png",
            "scope": "pages",
            "pages": "2",
            "width": 800,
            "height": 450,
            "scale": 1,
        })
        deadline = time.time() + 20
        job = {}
        while time.time() < deadline:
            with urllib.request.urlopen(base + "/api/jobs/" + submitted["job"]["id"]) as response:
                job = json.load(response)
            if job["status"] in {"succeeded", "failed"}:
                break
            time.sleep(0.1)
        assert job["status"] == "succeeded", job.get("error")
        download_url = job["result"]["files"][0]["download_url"]
        with urllib.request.urlopen(base + download_url) as response:
            assert response.headers.get_content_type() == "image/png"
            assert response.headers["Content-Disposition"].startswith("attachment;")
            assert response.read().startswith(b"\x89PNG")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_workbench_export_center_shows_real_manifest(tmp_path):
    project = make_project(tmp_path)
    server_app._OUTPUT_ROOT = tmp_path
    server = server_app.ThreadingHTTPServer(("127.0.0.1", 0), server_app._Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.add_init_script("localStorage.clear()")
            page.goto(base + "/")
            page.wait_for_function("document.querySelectorAll('.node').length >= 4")
            node_id = page.evaluate(
                """project => {
                    const ws = activeWorkspace();
                    const node = addNode('output', ws.x + ws.w + 80, ws.y + 30, {
                        workspaceId:ws.id, title:'导出演示 · 产物', project_name:project,
                        preview_url:'/output/' + encodeURIComponent(project) + '/output.html',
                        intent:'deck', preset_id:'fox-pixel-garden', revision:0, feedback:[],
                    });
                    select(node.id);
                    return node.id;
                }""",
                project.name,
            )
            page.get_by_role("button", name="导出 PDF / PNG").click()
            page.wait_for_selector("#export-analysis .export-score")
            assert page.locator("#export-analysis").get_by_text("检测到 2 个独立页面").is_visible()
            assert page.locator("#export-format").input_value() == "png"
            assert page.locator("#export-scope").input_value() == "pages"
            assert page.locator("#export-scale-field").is_visible()
            assert page.locator("#export-paper-field").is_hidden()
            assert page.locator("#export-landscape-field").is_hidden()
            assert page.locator("#export-start").is_enabled()
            assert page.evaluate("exportDraft.nodeId") == node_id
            assert not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def _json_request(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)
