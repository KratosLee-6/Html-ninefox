"""RC2 browser gates for revision comparison, accessibility, and large canvases."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

from htmlninefox import pipeline, revisions as revision_store
from htmlninefox.server import app as server_app


def start_server(root):
    server_app._OUTPUT_ROOT = root
    server = server_app.ThreadingHTTPServer(("127.0.0.1", 0), server_app._Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://127.0.0.1:{server.server_address[1]}", server, thread


def make_revision_project(root):
    project = root / "revision-demo"
    revisions = project / "revisions"
    revisions.mkdir(parents=True)
    old_html = "<!doctype html>\n<title>第一版</title>\n<main>旧内容</main>\n"
    new_html = "<!doctype html>\n<title>第二版</title>\n<main>新内容</main>\n"
    (revisions / "rev0.html").write_text(old_html, encoding="utf-8")
    (revisions / "rev1.html").write_text(new_html, encoding="utf-8")
    revision_store.atomic_write(project / "output.html", new_html)
    state = {
        "prompt": "版本差异演示",
        "intent": "landing",
        "preset_id": "fox-pixel-garden",
        "revision": 1,
        "created_at": "2026-09-18T12:00:00",
    }
    (project / pipeline.STATE_FILE).write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    revision_store.snapshot(project, {**state, "revision": 0}, old_html)
    revision_store.snapshot(project, state, new_html, kind="feedback", parent_revision=0)


def test_rc2_revision_dialog_accessibility_and_100_node_gate(tmp_path):
    make_revision_project(tmp_path)
    base, server, thread = start_server(tmp_path)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.add_init_script("localStorage.clear()")
            page.goto(base + "/")
            page.wait_for_function(
                "window.FoxInteraction && window.FoxCanvasProductivity && nodes.length >= 5",
                timeout=15000,
            )

            assert page.locator("#viewport").get_attribute("aria-label") == "无限画布工作区"
            assert page.locator("#minimap-svg").get_attribute("role") == "button"
            assert page.locator("#minimap-svg").get_attribute("tabindex") == "0"
            assert page.locator("#canvas-undo").get_attribute("aria-label") == "撤销 Ctrl+Z"
            assert page.locator("iframe:not([title])").count() == 0
            for selector in ("#preview-modal", "#export-modal", "#create-modal", "#ai-modal", "#memory-modal", "#revision-modal"):
                dialog = page.locator(selector)
                assert dialog.get_attribute("role") == "dialog"
                assert dialog.get_attribute("aria-modal") == "true"
                title_id = dialog.get_attribute("aria-labelledby")
                assert title_id and page.locator("#" + title_id).count() == 1

            output_id = page.evaluate("""() => {
                const ws = activeWorkspace();
                const node = addNode('output', ws.x + ws.w + 80, ws.y + 80, {
                    title:'版本差异演示 · 产物', project_name:'revision-demo',
                    preview_url:'/output/revision-demo/output.html', intent:'landing',
                    preset_id:'fox-pixel-garden', revision:1, feedback:[], workspaceId:ws.id,
                });
                select(node.id);
                return node.id;
            }""")
            diff_button = page.locator("#btn-revision-diff")
            assert diff_button.is_visible()
            diff_button.click()
            page.wait_for_function("document.querySelector('#revision-code').textContent.includes('第二版')")
            assert page.locator("#revision-from option").count() == 2
            assert page.locator("#revision-to option").count() == 2
            assert "新增 2 行" in page.locator("#revision-summary").inner_text()
            assert page.evaluate("document.activeElement?.id") == "revision-close"
            # Both ends of the modal's keyboard loop remain inside the dialog.
            page.keyboard.press("Shift+Tab")
            assert page.evaluate("document.activeElement?.id") == "revision-code"
            page.keyboard.press("Tab")
            assert page.evaluate("document.activeElement?.id") == "revision-close"
            page.locator("#revision-to").select_option("0")
            page.locator("#revision-label").fill('客户稿 <img src=x onerror="window.injected=true">')
            page.locator("#revision-save-label").click()
            page.wait_for_function("document.querySelector('#revision-history').textContent.includes('客户稿')")
            assert page.locator("#revision-history img").count() == 0
            assert page.evaluate("window.injected === undefined")
            page.locator("#revision-label").fill("客户确认稿")
            page.locator("#revision-save-label").click()
            page.wait_for_function("document.querySelector('#revision-label').value === '客户确认稿' && !document.querySelector('#revision-save-label').disabled")
            page.locator("#revision-restore").click()
            page.wait_for_function("document.querySelector('#revision-to').value === '2'")
            assert "恢复自 rev0" in page.locator("#revision-history").inner_text()
            assert page.evaluate("nodes.find(n => n.data?.project_name === 'revision-demo').data.revision") == 2
            assert (tmp_path / "revision-demo/output.html").read_bytes() == (tmp_path / "revision-demo/revisions/rev0.html").read_bytes()
            evidence = Path(os.environ["HTMLNINEFOX_TEST_EVIDENCE_DIR"]) if os.environ.get("HTMLNINEFOX_TEST_EVIDENCE_DIR") else None
            if evidence:
                evidence.mkdir(parents=True, exist_ok=True)
                for button in page.locator(".fox-toast-close").all():
                    button.click()
                page.wait_for_function("document.querySelectorAll('.fox-toast').length === 0")
                page.screenshot(path=str(evidence / "revision-history-desktop.png"))
            page.set_viewport_size({"width": 390, "height": 844})
            bounds = page.locator(".revision-dialog").bounding_box()
            assert bounds and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= 391
            assert page.evaluate("document.querySelector('.revision-body').scrollWidth <= document.querySelector('.revision-body').clientWidth + 1")
            if evidence:
                page.screenshot(path=str(evidence / "revision-history-mobile.png"))
            page.keyboard.press("Escape")
            page.wait_for_function(
                "document.querySelector('#revision-modal').hidden && document.activeElement?.id === 'btn-revision-diff'"
            )
            page.set_viewport_size({"width": 1440, "height": 900})

            metrics = page.evaluate("""async () => {
                nodes.splice(0); edges.splice(0); selectedIds.clear(); selected = null;
                document.querySelector('#nodes').innerHTML = '';
                const startRender = performance.now();
                for (let index = 0; index < 100; index += 1) {
                    const node = {
                        id:index + 1, kind:'note', x:80 + (index % 10) * 270,
                        y:80 + Math.floor(index / 10) * 170, w:226, h:120,
                        workspaceId:null, title:'性能节点 ' + (index + 1), data:{},
                    };
                    nodes.push(node); renderNode(node);
                }
                uid = 101;
                for (let index = 1; index < 100; index += 1) {
                    edges.push({from:index, to:index + 1});
                }
                const renderMs = performance.now() - startRender;
                const startEdges = performance.now();
                drawEdges();
                const edgeMs = performance.now() - startEdges;
                const startSelect = performance.now();
                const hits = FoxCanvasProductivity.selectWithin(
                    {x1:0, y1:0, x2:3000, y2:1900}, false, {contained:false}
                );
                const selectMs = performance.now() - startSelect;
                const startMove = performance.now();
                for (const node of nodes) { node.x += 8; node.y += 8; placeNode(node); }
                drawEdges();
                const moveMs = performance.now() - startMove;
                await persistWorkspaceNow();
                const saved = await api('/api/workspace');
                return {
                    renderMs, edgeMs, selectMs, moveMs, hits:hits.length,
                    nodes:document.querySelectorAll('.node').length,
                    edges:document.querySelectorAll('#edges path[data-edge]').length,
                    savedNodes:saved.state.canvas.nodes.length,
                };
            }""")
            assert metrics["nodes"] == 100
            assert metrics["edges"] == 99
            assert metrics["hits"] == 100
            assert metrics["savedNodes"] == 100
            assert metrics["renderMs"] < 3000, metrics
            assert metrics["edgeMs"] < 1500, metrics
            assert metrics["selectMs"] < 500, metrics
            assert metrics["moveMs"] < 2000, metrics
            if evidence:
                (evidence / "canvas-100-nodes.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
            assert not errors
            assert output_id > 0
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
