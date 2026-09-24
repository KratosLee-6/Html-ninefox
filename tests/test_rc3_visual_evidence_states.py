"""RC3 visual evidence gates for command, memory, error, and recovery states."""

from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from htmlninefox import pipeline, revisions as revision_store


def _make_revision_project(root: Path) -> None:
    project = root / "revision-visual-demo"
    revisions = project / "revisions"
    revisions.mkdir(parents=True)
    old_html = "<!doctype html>\n<title>第一版</title>\n<main>恢复目标：纸白产品页</main>\n"
    new_html = "<!doctype html>\n<title>第二版</title>\n<main>当前版本：夜蓝实验稿</main>\n"
    (revisions / "rev0.html").write_text(old_html, encoding="utf-8")
    (revisions / "rev1.html").write_text(new_html, encoding="utf-8")
    revision_store.atomic_write(project / "output.html", new_html)
    state = {
        "prompt": "RC3 版本恢复视觉验收",
        "intent": "landing",
        "preset_id": "fox-pixel-garden",
        "revision": 1,
        "created_at": "2026-09-24T18:00:00",
    }
    (project / pipeline.STATE_FILE).write_text(
        json.dumps(state, ensure_ascii=False), encoding="utf-8"
    )
    revision_store.snapshot(project, {**state, "revision": 0}, old_html)
    revision_store.snapshot(
        project, state, new_html, kind="feedback", parent_revision=0
    )


def _capture(page: Page, name: str) -> None:
    evidence_dir = os.environ.get("HTMLNINEFOX_RC3_EVIDENCE_DIR")
    if not evidence_dir:
        return
    target = Path(evidence_dir)
    target.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(target / name), full_page=False)


def test_rc3_command_memory_error_and_restore_states(tmp_path, workbench_server):
    _make_revision_project(tmp_path)
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("localStorage.clear()")
        page.goto(server.base_url + "/")
        page.wait_for_function(
            "window.FoxInteraction && window.FoxCanvasProductivity && window.FoxWorkbenchUI && nodes.length >= 5"
        )

        page.keyboard.press("Control+K")
        page.wait_for_selector("#canvas-command:not([hidden])")
        page.fill("#canvas-command-input", "生成")
        page.wait_for_selector("#canvas-command-results [role='option']")
        assert page.locator("[data-command-id='advance']").count() == 1
        assert page.evaluate("document.activeElement?.id") == "canvas-command-input"
        assert page.locator("#canvas-command-results [role='option']").count() >= 1
        _capture(page, "command-palette-search.png")
        page.keyboard.press("Escape")

        page.click("#btn-memory")
        page.wait_for_selector("#memory-modal:not([hidden])")
        page.fill("#memory-brand", "Html九尾狐")
        page.fill("#memory-audience", "设计师、开发者与内容团队")
        page.fill("#memory-tone", "清晰、温暖、专业")
        page.fill("#memory-forbidden", "黑紫 AI 渐变\n无意义装饰动效")
        page.fill("#memory-template", "fox-pixel-garden")
        page.fill("#memory-primary", "#173C8F")
        page.fill("#memory-notes", "保持纸张质感、像素狐狸和真实 HTML 交付。")
        page.click("#memory-save")
        page.wait_for_function(
            "document.querySelector('#memory-status').textContent.includes('已保存')"
        )
        assert page.locator("#memory-status").get_attribute("role") == "status"
        page.locator("#memory-modal .flow-body").evaluate("element => element.scrollTop = 0")
        page.wait_for_timeout(220)
        _capture(page, "project-memory-saved.png")
        page.locator("#memory-modal .preview-bar button").click()

        missing_output_id = page.evaluate(
            """() => {
                const ws = activeWorkspace();
                const node = addNode('output', ws.x + ws.w + 80, ws.y + 80, {
                    title:'导出错误演示 · 产物', project_name:'missing-export-demo',
                    preview_url:'', intent:'landing', preset_id:'fox-pixel-garden',
                    revision:0, feedback:[], workspaceId:ws.id,
                });
                select(node.id);
                return node.id;
            }"""
        )
        page.evaluate("nodeId => openExportCenter(nodeId)", missing_output_id)
        page.wait_for_function(
            "document.querySelector('#export-status').textContent === '分析失败'"
        )
        assert page.locator("#export-analysis .export-warning.error").is_visible()
        assert page.locator("#export-start").is_disabled()
        assert page.locator("#export-status").get_attribute("role") == "status"
        assert page.locator(".fox-toast[data-toast-type='error']").count() >= 1
        _capture(page, "export-analysis-error.png")
        page.evaluate("closeExportCenter()")
        page.locator(".fox-toast[data-toast-type='error'] .fox-toast-close").click()
        page.wait_for_function("document.querySelectorAll('.fox-toast[data-toast-type=error]').length === 0")

        restore_output_id = page.evaluate(
            """() => {
                const ws = activeWorkspace();
                const node = addNode('output', ws.x + ws.w + 80, ws.y + 360, {
                    title:'版本恢复演示 · 产物', project_name:'revision-visual-demo',
                    preview_url:'/output/revision-visual-demo/output.html', intent:'landing',
                    preset_id:'fox-pixel-garden', revision:1, feedback:[], workspaceId:ws.id,
                });
                select(node.id);
                return node.id;
            }"""
        )
        page.evaluate("nodeId => openRevisionDiff(nodeId)", restore_output_id)
        page.wait_for_function(
            "document.querySelector('#revision-code').textContent.includes('当前版本')"
        )
        page.locator("#revision-to").select_option("0")
        page.locator("#revision-restore").click()
        page.wait_for_function("document.querySelector('#revision-to').value === '2'")
        assert "恢复自 rev0" in page.locator("#revision-history").inner_text()
        assert "已从 rev0 恢复为 rev2" in page.locator(".fox-toast[data-toast-type='success']").last.inner_text()
        assert page.evaluate(
            "nodes.find(node => node.data?.project_name === 'revision-visual-demo').data.revision"
        ) == 2
        assert (tmp_path / "revision-visual-demo" / "output.html").read_bytes() == (
            tmp_path / "revision-visual-demo" / "revisions" / "rev0.html"
        ).read_bytes()
        _capture(page, "revision-restore-complete.png")

        assert not errors
        browser.close()
