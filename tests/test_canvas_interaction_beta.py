"""Browser regression coverage for v0.5 beta canvas interactions."""

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


def test_canvas_geometry_snap_hysteresis_and_final_pointer_frame(tmp_path):
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

            geometry = page.evaluate("""() => {
                camera = {x:90, y:70, z:1.25};
                applyCamera(false);
                const node = nodes.find(item => item.kind === 'block');
                const port = document.querySelector('#node-' + node.id + ' .port-out');
                const rect = port.getBoundingClientRect();
                const point = canvasEngine.portPoint(node.id, 'out');
                const viewportRect = viewport.getBoundingClientRect();
                const projected = {
                    x:viewportRect.left + camera.x + point.x * camera.z,
                    y:viewportRect.top + camera.y + point.y * camera.z,
                };
                return {
                    dx:Math.abs(projected.x - (rect.left + rect.width / 2)),
                    dy:Math.abs(projected.y - (rect.top + rect.height / 2)),
                };
            }""")
            assert geometry["dx"] < 0.25
            assert geometry["dy"] < 0.25

            snapping = page.evaluate("""() => {
                camera = {x:0, y:0, z:1};
                applyCamera(false);
                const moving = nodes.find(item => item.kind === 'requirement');
                const target = nodes.find(item => item.kind === 'template');
                const session = canvasEngine.createSnapSession();
                const first = canvasEngine.snapNode(moving, target.x + 3, moving.y, {
                    grid:false, session,
                });
                const held = canvasEngine.snapNode(moving, target.x + 11, moving.y, {
                    grid:false, session,
                });
                const released = canvasEngine.snapNode(moving, target.x + 18, moving.y, {
                    grid:false, session,
                });
                const excluded = nodes.map(item => item.id);
                const fluid = canvasEngine.snapNode(moving, 123, 457, {
                    grid:false, excludeIds:excluded,
                });
                const legacyGrid = canvasEngine.snapNode(moving, 123, 457, false, excluded);
                return { targetX:target.x, first, held, released, fluid, legacyGrid };
            }""")
            assert snapping["first"]["x"] == snapping["targetX"]
            assert snapping["held"]["x"] == snapping["targetX"]
            assert snapping["released"]["x"] == snapping["targetX"] + 18
            assert snapping["fluid"]["x"] == 123
            assert snapping["legacyGrid"]["x"] == 128

            sticky_target = page.evaluate("""() => {
                const target = nodes.find(item => item.kind === 'template');
                const port = document.querySelector('#node-' + target.id + ' .port-in');
                const rect = port.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                const acquired = canvasEngine.nearestInput(centerX + 28, centerY, -1);
                const held = canvasEngine.nearestInput(centerX + 42, centerY, -1, acquired);
                const released = canvasEngine.nearestInput(centerX + 58, centerY, -1, held);
                return {
                    targetId:target.id,
                    acquired:acquired?.nodeId || null,
                    held:held?.nodeId || null,
                    released:released?.nodeId || null,
                };
            }""")
            assert sticky_target["acquired"] == sticky_target["targetId"]
            assert sticky_target["held"] == sticky_target["targetId"]
            assert sticky_target["released"] != sticky_target["targetId"]

            final_frame = page.evaluate("""() => {
                camera = {x:0, y:0, z:1};
                applyCamera(false);
                const ws = activeWorkspace();
                const node = addNode('note', ws.x + 610, ws.y + 360, {
                    title:'最终指针帧测试', workspaceId:ws.id,
                });
                const element = document.getElementById('node-' + node.id);
                const handle = element.querySelector('.node-head') || element;
                const rect = handle.getBoundingClientRect();
                Object.defineProperty(viewport, 'setPointerCapture', { configurable:true, value:() => {} });
                const start = {x:node.x, y:node.y};
                handle.dispatchEvent(new PointerEvent('pointerdown', {
                    bubbles:true, pointerId:701, isPrimary:true,
                    clientX:rect.left + 30, clientY:rect.top + 14,
                }));
                window.dispatchEvent(new PointerEvent('pointerup', {
                    bubbles:true, pointerId:701, isPrimary:true, altKey:true,
                    clientX:rect.left + 53, clientY:rect.top + 33,
                }));
                return { dx:node.x - start.x, dy:node.y - start.y };
            }""")
            assert final_frame == {"dx": 23, "dy": 19}

            assert not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_workspace_header_drag_uses_visible_handle(tmp_path):
    base, server, thread = start_server(tmp_path)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.add_init_script("localStorage.clear()")
            page.goto(base + "/")
            page.wait_for_function(
                "window.FoxCanvasProductivity && document.querySelector('.ws-head')",
                timeout=15000,
            )
            page.wait_for_timeout(250)
            before = page.evaluate("({x:nodes.find(node => node.kind === 'ws').x, y:nodes.find(node => node.kind === 'ws').y})")
            box = page.locator(".ws-head").first.bounding_box()
            hit = page.evaluate(
                "([x,y]) => { const el=document.elementFromPoint(x,y); return {tag:el?.tagName, className:el?.className || '', text:el?.textContent || ''}; }",
                [box["x"] + 30, box["y"] + 12],
            )
            page.mouse.move(box["x"] + 30, box["y"] + 12)
            page.mouse.down()
            page.mouse.move(box["x"] + 130, box["y"] + 60, steps=8)
            page.mouse.up()
            after = page.evaluate("({x:nodes.find(node => node.kind === 'ws').x, y:nodes.find(node => node.kind === 'ws').y})")
            assert after != before, f"visible hit target did not drag workspace: {hit}"
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_visible_card_drag_and_port_linking(tmp_path):
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
                "window.FoxCanvasProductivity && nodes.length >= 5",
                timeout=15000,
            )
            page.wait_for_timeout(300)

            body = page.locator(".node.requirement .node-body").first
            box = body.bounding_box()
            hit = page.evaluate(
                "([x,y]) => { const el=document.elementFromPoint(x,y); return {tag:el?.tagName, className:el?.className || '', id:el?.id || ''}; }",
                [box["x"] + 15, box["y"] + 4],
            )
            before = page.evaluate("({x:nodes.find(node => node.kind === 'requirement').x, y:nodes.find(node => node.kind === 'requirement').y})")
            page.mouse.move(box["x"] + 15, box["y"] + 4)
            page.mouse.down()
            page.mouse.move(box["x"] + 138, box["y"] + 71, steps=8)
            page.mouse.up()
            page.wait_for_timeout(80)
            after = page.evaluate("({x:nodes.find(node => node.kind === 'requirement').x, y:nodes.find(node => node.kind === 'requirement').y})")
            assert after != before, f"visible card body did not drag: {hit}"

            ids = page.evaluate("""() => {
                const ws = activeWorkspace();
                const rect = viewport.getBoundingClientRect();
                const sourcePoint = canvasEngine.screenToWorld(rect.left + 400, rect.top + 420);
                const targetPoint = canvasEngine.screenToWorld(rect.left + 700, rect.top + 420);
                const source = addNode('block', sourcePoint[0], sourcePoint[1], {title:'连线源', blockId:'features', workspaceId:ws.id});
                const target = addNode('block', targetPoint[0], targetPoint[1], {title:'连线目标', blockId:'steps', workspaceId:ws.id});
                source.x = sourcePoint[0]; source.y = sourcePoint[1]; placeNode(source);
                target.x = targetPoint[0]; target.y = targetPoint[1]; placeNode(target);
                return {source:source.id, target:target.id};
            }""")
            source = page.locator(f'#node-{ids["source"]} .port-out').bounding_box()
            target = page.locator(f'#node-{ids["target"]} .port-in').bounding_box()
            source_center = [source["x"] + source["width"] / 2, source["y"] + source["height"] / 2]
            target_center = [target["x"] + target["width"] / 2, target["y"] + target["height"] / 2]
            hits = page.evaluate(
                "([sx,sy,tx,ty]) => [document.elementFromPoint(sx,sy)?.className || '', document.elementFromPoint(tx,ty)?.className || '']",
                [*source_center, *target_center],
            )
            page.mouse.move(*source_center)
            page.mouse.down()
            page.mouse.move(*target_center, steps=12)
            page.wait_for_timeout(80)
            assert page.locator(f'#node-{ids["target"]} .port-in').evaluate("element => element.classList.contains('link-target')"), hits
            page.mouse.up()
            assert page.evaluate("ids => edges.some(edge => edge.from === ids.source && edge.to === ids.target)", ids)
            assert not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
