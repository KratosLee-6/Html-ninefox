"""End-to-end coverage for gallery selection and guided creation flow."""

from __future__ import annotations

import json
import threading

from playwright.sync_api import sync_playwright

from htmlninefox import pipeline
from htmlninefox.server import app as server_app


def start_server(root):
    server_app._OUTPUT_ROOT = root
    server = server_app.ThreadingHTTPServer(("127.0.0.1", 0), server_app._Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://127.0.0.1:{server.server_address[1]}", server, thread


def test_gallery_pages_are_visible_and_extractable(tmp_path):
    base, server, thread = start_server(tmp_path)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/")
            page.wait_for_timeout(1200)

            assert page.locator("#pal .gallery-card").count() >= 6
            page.wait_for_function(
                "Boolean(document.querySelector('#pal .gallery-card iframe')?.contentDocument?.querySelector('.page.on'))"
            )
            page.locator("#pal .preview-open").first.click()
            page.wait_for_selector("#preview-pages:not([hidden])")
            assert page.locator(".preview-page").count() >= 5
            page.locator(".preview-page").nth(1).click()
            page.locator("#preview-extract-page").click()

            assert page.evaluate("nodes.some(node => node.kind === 'block' && node.data.gallery_id)")
            assert not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_guided_input_analysis_and_generation_persist_composition(tmp_path):
    base, server, thread = start_server(tmp_path)
    reference = tmp_path / "reference.md"
    reference.write_text("目标：展示真实模板、AI 推荐和本地数据安全。", encoding="utf-8")
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/")
            page.wait_for_timeout(1000)

            page.get_by_role("button", name="输入需求").click()
            page.fill(
                "#creation-prompt",
                "做一个 AI 原生创作工具发布会 PPT，重点展示模板作品库、自由组合和 API Key 自主管理",
            )
            page.set_input_files("#creation-files", str(reference))
            page.wait_for_function("creationDraft.inputs.length === 1")
            page.click("#creation-analyze")
            page.wait_for_selector("text=采用推荐并生成", timeout=10000)
            page.get_by_role("button", name="采用推荐并生成").click()
            page.wait_for_selector(".node.output", timeout=30000)

            project_name = page.evaluate("nodes.find(node => node.kind === 'output').data.project_name")
            state = json.loads((tmp_path / project_name / pipeline.STATE_FILE).read_text(encoding="utf-8"))
            composition = state["composition"]
            assert composition["gallery_id"]
            assert len(composition["blocks"]) >= 5
            assert composition["inputs"][0]["name"] == "reference.md"
            assert composition["selection_mode"] == "recommended"
            assert page.evaluate("nodes.filter(node => node.kind === 'source').length") == 1
            assert not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
