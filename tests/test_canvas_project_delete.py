"""Browser regression tests for deleting canvas project nodes."""

from __future__ import annotations

import threading

from playwright.sync_api import sync_playwright

from htmlninefox.server import app as server_app


def test_missing_project_can_be_removed_from_canvas(tmp_path):
    server_app._OUTPUT_ROOT = tmp_path
    server = server_app.ThreadingHTTPServer(("127.0.0.1", 0), server_app._Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(base + "/")
            page.evaluate("localStorage.clear()")
            page.reload()
            page.wait_for_timeout(300)
            output_id = page.evaluate("""() => {
                const node = addNode('output', 620, 220, {
                    title: '已失效产物',
                    project_name: 'missing-project',
                    intent: 'landing',
                    preset_id: 'fox-pixel-garden',
                    revision: 0,
                });
                select(node.id);
                return node.id;
            }""")
            page.once("dialog", lambda dialog: dialog.accept())
            page.locator("#inspector .btn-danger-ghost").click()
            page.wait_for_timeout(200)

            assert page.evaluate("id => !nodes.some(node => node.id === id)", output_id)
            assert "已从画布移除" in page.locator("#tl-status").inner_text()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
