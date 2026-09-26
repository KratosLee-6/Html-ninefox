"""v0.6 / RC3-E: isolated workbench lifecycle modules, race guards, and cancel."""

from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from htmlninefox import intake, pipeline

READY = ("window.FoxInteraction && window.FoxCanvasProductivity && window.FoxWorkbenchUI"
         " && window.FoxProjects && window.FoxGeneration && window.FoxRevisions"
         " && window.FoxExports && nodes.length >= 5")


def _capture(page, name: str) -> None:
    evidence_dir = os.environ.get("HTMLNINEFOX_RC3_EVIDENCE_DIR")
    if not evidence_dir:
        return
    target = Path(evidence_dir)
    target.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(target / name), full_page=False)


def _wait_for_requirement_text(page, text: str) -> None:
    page.wait_for_function(
        """text => {
            const ws = activeWorkspace();
            const req = membersOf(ws).find(n => n.kind === 'requirement')
                || membersOf(ws).find(n => n.kind === 'note');
            if (!req) return false;
            req.data.text = text;
            const el = document.getElementById('node-' + req.id);
            const area = el && el.querySelector('textarea');
            if (area) area.value = text;
            return true;
        }""", arg=text)


def test_lifecycle_modules_expose_namespaced_apis_and_global_shims(
        tmp_path, workbench_server):
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("localStorage.clear()")
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)

        apis = page.evaluate(
            """() => ({
                projects: Object.keys(window.FoxProjects).sort(),
                generation: Object.keys(window.FoxGeneration).sort(),
                revisions: Object.keys(window.FoxRevisions).sort(),
                exports: Object.keys(window.FoxExports).sort(),
                shims: [typeof openRevisionDiff, typeof openExportCenter,
                        typeof advanceWs, typeof startExport, typeof cancelGeneration],
                draftsPrivate: [typeof exportDraft, typeof revisionDraft],
            })"""
        )
        assert "load" in apis["projects"] and "trash" in apis["projects"]
        assert "advance" in apis["generation"] and "cancelActive" in apis["generation"]
        assert "restore" in apis["revisions"] and "sendFeedback" in apis["revisions"]
        assert "start" in apis["exports"] and "draft" in apis["exports"]
        assert apis["shims"] == ["function", "function", "function", "function", "function"]
        # Module draft state is no longer a global variable.
        assert apis["draftsPrivate"] == ["undefined", "undefined"]
        assert errors == []
        browser.close()


def test_rapid_double_advance_is_rejected_and_produces_one_result(
        tmp_path, workbench_server):
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("localStorage.clear()")
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)
        _wait_for_requirement_text(page, "做一个极简的落地页，介绍本地优先的 HTML 工作台")

        ws_id = page.evaluate("activeWorkspace().id")
        page.evaluate("id => void advanceWs(id)", ws_id)
        # 快速二次推进：应被 epoch 守卫拒绝，不产生第二个任务
        page.evaluate("id => void advanceWs(id)", ws_id)
        page.wait_for_function(
            "document.querySelector('#tl-status').textContent.includes('该工作区正在推进')")

        page.wait_for_selector(".node.output", timeout=30000)
        page.wait_for_function("document.querySelectorAll('.node.output').length === 1")
        page.wait_for_function(
            "FoxGeneration.generatingNodes.size === 0 && FoxGeneration.generationCleanups.size === 0")
        assert not page.locator("#btn-cancel-gen").is_visible()
        assert errors == []
        browser.close()


def test_cancel_generation_aborts_waiting_with_honest_feedback(
        tmp_path, workbench_server):
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("localStorage.clear()")

        # 让任务提交响应停在路上，保证取消点确定落在等待阶段
        def hold_submit(route):
            if "api/jobs" in route.request.url and route.request.method == "POST":
                page.wait_for_timeout(1200)
            route.continue_()

        page.route("**/*", hold_submit)
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)
        _wait_for_requirement_text(page, "做一个取消演示落地页")

        ws_id = page.evaluate("activeWorkspace().id")
        page.evaluate("id => void advanceWs(id)", ws_id)
        page.wait_for_selector("#btn-cancel-gen:not([hidden])")
        page.locator("#btn-cancel-gen").click()

        page.wait_for_function(
            "document.querySelector('#tl-status').textContent.includes('已停止等待本次生成')")
        page.wait_for_function("!document.getElementById('btn-cancel-gen').offsetParent")
        page.wait_for_function(
            "FoxGeneration.generatingNodes.size === 0 && FoxGeneration.generationCleanups.size === 0")
        _capture(page, "generation-cancel.png")
        assert page.locator(".node.output").count() == 0
        assert errors == []
        browser.close()


def test_export_start_is_guarded_while_a_job_is_running(tmp_path, workbench_server):
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("localStorage.clear()")

        work = pipeline.run_expert(
            "做一个导出守卫演示落地页", output=str(server.output_root), quiet_llm=True)["work"]
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)
        node_id = page.evaluate(
            """project => {
                const ws = activeWorkspace();
                const node = addNode('output', ws.x + ws.w + 80, ws.y + 80, {
                    title:'导出守卫 · 产物', project_name: project,
                    preview_url:'/output/' + project + '/output.html',
                    intent:'landing', preset_id:'fox-pixel-garden',
                    revision:0, feedback:[], workspaceId:ws.id,
                });
                select(node.id);
                return node.id;
            }""", work.name)

        def hold_export(route):
            if "api/exports" in route.request.url and route.request.method == "POST":
                page.wait_for_timeout(1000)
            route.continue_()

        page.route("**/*", hold_export)
        page.evaluate("nodeId => openExportCenter(nodeId)", node_id)
        page.wait_for_function(
            "document.querySelector('#export-status').textContent === '分析完成，可以导出'")
        page.locator("#export-start").click()
        page.wait_for_function("!document.getElementById('export-start').disabled === false")
        # busy 守卫：进行中再次触发 start 直接被拒，不提交第二个任务
        busy_flash = page.evaluate(
            "() => { FoxExports.start(); return document.querySelector('#tl-status').textContent; }")
        assert "已有导出正在进行" in busy_flash
        page.wait_for_function(
            "document.querySelector('#export-status').textContent.includes('导出完成')", timeout=60000)
        page.unroute("**/*", hold_export)
        assert not page.locator("#export-start").is_disabled()
        assert errors == []
        browser.close()


def test_intake_workbench_dialog_lists_candidates(tmp_path: Path, workbench_server) -> None:
    sample = (b"<!doctype html><html><head><title>UI Inspo Board</title>"
              b"<style>body{color:#173C8F}</style></head><body><main><h1>Board</h1></main></body></html>")
    evidence = {
        "url": "https://example.com/board", "final_url": "https://example.com/board",
        "followed": ["https://example.com/board"], "status": 200,
        "content_type": "text/html", "body": sample, "body_sha256": "1" * 64,
        "body_bytes": len(sample), "fetched_at": "2026-09-26T09:00:00",
    }
    candidate = intake.extract_candidate(
        evidence, source={"id": "land-book", "license_class": "reference"})
    with workbench_server as server:
        intake.CandidateStore(server.output_root).save(candidate, evidence)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            # 沙箱预览 iframe 是不透明源，localStorage 不可用——init 脚本需容错
            page.add_init_script("try{localStorage.clear()}catch(e){}")
            page.goto(server.base_url + "/")
            page.wait_for_function(
                "window.FoxInteraction && window.FoxIntake && nodes.length >= 5")
            page.evaluate("openIntake()")
            page.wait_for_selector("#intake-modal:not([hidden])")
            page.wait_for_function(
                "document.querySelector('#intake-list').textContent.includes('UI Inspo Board')")
            assert page.locator(".intake-card").count() == 1
            assert page.locator("#intake-source option").count() >= 3
            _capture(page, "intake-review.png")
            assert errors == []
            browser.close()
