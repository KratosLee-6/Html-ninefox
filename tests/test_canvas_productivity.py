"""Browser coverage for canvas productivity interactions."""

from __future__ import annotations

import threading

from playwright.sync_api import sync_playwright

from htmlninefox.server import app as server_app


def start_server(root):
    server_app._OUTPUT_ROOT = root
    server = server_app.ThreadingHTTPServer(("127.0.0.1", 0), server_app._Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://127.0.0.1:{server.server_address[1]}", server, thread


def test_canvas_productivity_workflow(tmp_path):
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
                "window.FoxCanvasProductivity && document.querySelectorAll('.node').length >= 4",
                timeout=15000,
            )

            created = page.evaluate("""() => {
                const ws = activeWorkspace();
                const first = addNode('block', ws.x + 90, ws.y + 100, {
                    title:'组合测试 A', blockId:'hero', workspaceId:ws.id,
                });
                const second = addNode('block', ws.x + 390, ws.y + 100, {
                    title:'组合测试 B', blockId:'features', workspaceId:ws.id,
                });
                FoxCanvasProductivity.commitHistory();
                return { first:first.id, second:second.id, count:nodes.length };
            }""")

            page.evaluate("ids => selectMany([ids.first, ids.second])", created)
            assert page.evaluate("selectedIds.size") == 2
            page.locator("#canvas-group").click()
            group_ids = page.evaluate(
                "ids => [nodes.find(n => n.id === ids.first).groupId, nodes.find(n => n.id === ids.second).groupId]",
                created,
            )
            assert group_ids[0] and group_ids[0] == group_ids[1]

            before = page.evaluate(
                "ids => [ids.first, ids.second].map(id => ({...nodes.find(n => n.id === id)}))",
                created,
            )
            first_box = page.locator(f"#node-{created['first']} .node-head").bounding_box()
            page.mouse.move(first_box["x"] + 30, first_box["y"] + 15)
            page.mouse.down()
            page.mouse.move(first_box["x"] + 110, first_box["y"] + 75, steps=6)
            page.mouse.up()
            after = page.evaluate(
                "ids => [ids.first, ids.second].map(id => ({...nodes.find(n => n.id === id)}))",
                created,
            )
            assert (after[0]["x"], after[0]["y"]) != (before[0]["x"], before[0]["y"])
            assert after[0]["x"] - before[0]["x"] == after[1]["x"] - before[1]["x"]
            assert after[0]["y"] - before[0]["y"] == after[1]["y"] - before[1]["y"]

            page.locator("#canvas-lock").click()
            assert page.evaluate(
                "ids => [ids.first, ids.second].every(id => nodes.find(n => n.id === id).locked)",
                created,
            )
            locked_before = page.evaluate(
                "id => ({x:nodes.find(n => n.id === id).x, y:nodes.find(n => n.id === id).y})",
                created["first"],
            )
            first_box = page.locator(f"#node-{created['first']} .node-head").bounding_box()
            page.mouse.move(first_box["x"] + 30, first_box["y"] + 15)
            page.mouse.down()
            page.mouse.move(first_box["x"] + 100, first_box["y"] + 60)
            page.mouse.up()
            locked_after = page.evaluate(
                "id => ({x:nodes.find(n => n.id === id).x, y:nodes.find(n => n.id === id).y})",
                created["first"],
            )
            assert locked_after == locked_before

            page.locator("#canvas-lock").click()
            selection = page.evaluate("""ids => {
                const first = nodes.find(n => n.id === ids.first);
                const second = nodes.find(n => n.id === ids.second);
                return FoxCanvasProductivity.selectWithin({
                    x1:Math.min(first.x, second.x) - 2,
                    y1:Math.min(first.y, second.y) - 2,
                    x2:Math.max(first.x + first.w, second.x + second.w) + 2,
                    y2:Math.max(first.y + 160, second.y + 160) + 2,
                });
            }""", created)
            assert set(selection) >= {created["first"], created["second"]}

            page.keyboard.press("Control+K")
            page.fill("#canvas-command-input", "组合测试 A")
            page.locator(f'[data-canvas-result="{created["first"]}"]').click()
            assert page.evaluate("selected") == created["first"]
            assert page.locator("#minimap-svg .minimap-node").count() >= created["count"]

            page.evaluate("""() => {
                const ws = activeWorkspace();
                addNode('note', ws.x + 620, ws.y + 350, {title:'撤销测试', workspaceId:ws.id});
                FoxCanvasProductivity.commitHistory();
            }""")
            page.keyboard.press("Control+Z")
            assert page.evaluate("!nodes.some(node => node.title === '撤销测试')")
            page.keyboard.press("Control+Y")
            assert page.evaluate("nodes.some(node => node.title === '撤销测试')")

            assert not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
