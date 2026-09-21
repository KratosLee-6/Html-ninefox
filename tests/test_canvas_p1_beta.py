"""Browser regression coverage for canvas P1 — edge incremental render, job progress ring, group container."""

from __future__ import annotations


from playwright.sync_api import sync_playwright



def test_edge_incremental_render_and_motion(tmp_path, workbench_server):
    """G4：drawEdges 走差量更新、新边生长、删除边淡出、预览线复用同一元素。"""
    with workbench_server as server:
        base = server.base_url
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
            page.wait_for_timeout(250)

            created = page.evaluate("""() => {
                const ws = activeWorkspace();
                const a = addNode('block', ws.x + 120, ws.y + 120, {title:'连线A', blockId:'hero', workspaceId:ws.id});
                const b = addNode('block', ws.x + 460, ws.y + 120, {title:'连线B', blockId:'features', workspaceId:ws.id});
                const before = edgesEl.querySelectorAll('path').length;
                edges.push({from:a.id, to:b.id});
                drawEdges();
                const key = a.id + '->' + b.id;
                const path = edgesEl.querySelector('path[data-edge="' + key + '"]');
                return {
                    a:a.id, b:b.id, before, key,
                    pathCount:edgesEl.querySelectorAll('path').length,
                    hasEnter:path ? path.classList.contains('edge-enter') : null,
                    pathLength:path ? path.getAttribute('pathLength') : null,
                    d:path ? path.getAttribute('d') : null,
                };
            }""")
            assert created["pathCount"] == created["before"] + 1
            assert created["hasEnter"] is True, "新边应带 .edge-enter 生长动画"
            assert created["pathLength"] == "1", "pathLength 归一是纯 CSS 生长动画的前提"
            assert created["d"] and created["d"].startswith("M ")

            # 同一 key 再画一次：复用同一个 DOM 元素（差量），且 d 跟随节点位置更新
            stable = page.evaluate(
                """payload => {
                    const first = edgesEl.querySelector('path[data-edge="' + payload.key + '"]');
                    const node = nodes.find(item => item.id === payload.a);
                    node.x += 40; placeNode(node);
                    drawEdges();
                    const second = edgesEl.querySelector('path[data-edge="' + payload.key + '"]');
                    return { same:first === second, moved:second.getAttribute('d') !== payload.d,
                             count:edgesEl.querySelectorAll('path[data-edge="' + payload.key + '"]').length };
                }""",
                created,
            )
            assert stable == {"same": True, "moved": True, "count": 1}, stable

            # 删除边：先挂 .edge-leave，再移除
            leaving = page.evaluate(
                """ids => {
                    edges = edges.filter(edge => !(edge.from === ids.a && edge.to === ids.b));
                    drawEdges();
                    return edgesEl.querySelectorAll('path.edge-leave').length;
                }""",
                created,
            )
            assert leaving == 1, "删除边应先进入 .edge-leave 淡出"
            page.wait_for_timeout(420)
            assert page.evaluate("edgesEl.querySelectorAll('path.edge-leave').length") == 0
            assert page.evaluate("edgesEl.querySelectorAll('path').length") == created["before"]

            # 预览线复用单元素
            preview = page.evaluate("""() => {
                tempEdge({x:0, y:0}, {x:100, y:0});
                const first = edgesEl.querySelector('path.temp');
                tempEdge({x:0, y:0}, {x:260, y:60});
                const second = edgesEl.querySelector('path.temp');
                const snapshot = {
                    same:first === second,
                    count:edgesEl.querySelectorAll('path.temp').length,
                    d:second.getAttribute('d'),
                };
                clearTempEdge();
                snapshot.cleared = edgesEl.querySelectorAll('path.temp').length;
                return snapshot;
            }""")
            assert preview["same"] is True and preview["count"] == 1, preview
            assert "260" in preview["d"]
            assert preview["cleared"] == 0

            assert not errors
            browser.close()


def test_node_generation_progress_ring(tmp_path, workbench_server):
    """G5：进度环吃真实百分比，成功 200ms 收敛、失败走陶土橙 #E57A3F。"""
    with workbench_server as server:
        base = server.base_url
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
            page.wait_for_timeout(250)

            idle = page.evaluate("""() => {
                const ws = activeWorkspace();
                const node = addNode('requirement', ws.x + 120, ws.y + 120, {title:'进度环', workspaceId:ws.id});
                return { id:node.id, rings:document.getElementById('node-' + node.id).querySelectorAll('[data-gen-ring]').length };
            }""")
            assert idle["rings"] == 0

            running = page.evaluate(
                """id => {
                    markNodeGenerating(id, null);
                    const el = document.getElementById('node-' + id);
                    const spin = { isGenerating:el.classList.contains('is-generating'),
                                   mode:el.querySelector('[data-gen-ring]').dataset.mode };
                    markNodeGenerating(id, 42);
                    const bar = el.querySelector('.gen-ring-bar');
                    return { spin, mode:el.querySelector('[data-gen-ring]').dataset.mode,
                             pct:el.querySelector('.gen-ring-pct').textContent,
                             dasharray:bar.style.strokeDasharray,
                             dashoffset:Number(bar.style.strokeDashoffset) };
                }""",
                idle["id"],
            )
            assert running["spin"] == {"isGenerating": True, "mode": "spin"}
            assert running["mode"] == "progress"
            assert running["pct"] == "42%"
            assert running["dasharray"] == "1"
            assert abs(running["dashoffset"] - 0.58) < 1e-6, running

            clamped = page.evaluate(
                """id => { markNodeGenerating(id, 140);
                    return document.querySelector('#node-' + id + ' .gen-ring-pct').textContent; }""",
                idle["id"],
            )
            assert clamped == "100%"

            # 失败：陶土橙 + is-gen-failed，随后自动清理
            failed = page.evaluate(
                """id => {
                    finishNodeGenerating(id, true);
                    const el = document.getElementById('node-' + id);
                    return { failed:el.classList.contains('is-gen-failed'),
                             generating:el.classList.contains('is-generating'),
                             mode:el.querySelector('[data-gen-ring]').dataset.mode };
                }""",
                idle["id"],
            )
            assert failed == {"failed": True, "generating": False, "mode": "failed"}
            assert page.evaluate(
                "getComputedStyle(document.querySelector('.gen-ring[data-mode=\"failed\"] .gen-ring-bar')).stroke === 'rgb(229, 122, 63)'"
            ), "失败态必须用陶土橙 #E57A3F"
            page.wait_for_timeout(2800)
            assert page.evaluate("document.querySelectorAll('[data-gen-ring]').length") == 0

            # 成功：is-gen-done 收敛后清理
            done = page.evaluate(
                """() => {
                    const ws = activeWorkspace();
                    const node = addNode('requirement', ws.x + 380, ws.y + 120, {title:'收敛', workspaceId:ws.id});
                    markNodeGenerating(node.id, 100);
                    finishNodeGenerating(node.id, false);
                    const el = document.getElementById('node-' + node.id);
                    return { done:el.classList.contains('is-gen-done'), generating:el.classList.contains('is-generating') };
                }"""
            )
            assert done == {"done": True, "generating": False}
            page.wait_for_timeout(500)
            assert page.evaluate("document.querySelectorAll('[data-gen-ring]').length") == 0

            assert not errors
            browser.close()


def test_group_container_wrap_drag_and_rename(tmp_path, workbench_server):
    """G7：组框容器自动包裹成员 bounds、拖动容器整组移动、双击组名重命名。"""
    with workbench_server as server:
        base = server.base_url
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.add_init_script("localStorage.clear()")
            page.goto(base + "/")
            page.wait_for_function(
                "window.FoxCanvasProductivity && window.FoxCanvasGroups && document.querySelectorAll('.node').length >= 4",
                timeout=15000,
            )
            page.wait_for_timeout(250)

            created = page.evaluate("""() => {
                const ws = activeWorkspace();
                const a = addNode('block', ws.x + 120, ws.y + 140, {title:'组A', blockId:'hero', workspaceId:ws.id});
                const b = addNode('block', ws.x + 340, ws.y + 140, {title:'组B', blockId:'features', workspaceId:ws.id});
                a.x = ws.x + 120; a.y = ws.y + 140; placeNode(a);
                b.x = ws.x + 340; b.y = ws.y + 140; placeNode(b);
                selectMany([a.id, b.id]);
                FoxCanvasProductivity.groupSelection();
                const box = document.querySelector('.group-box');
                const groupId = box ? box.dataset.group : null;
                return { a:a.id, b:b.id, count:document.querySelectorAll('.group-box').length, groupId,
                         label:box ? box.querySelector('.group-label').textContent : null,
                         bounds:groupId ? FoxCanvasGroups.bounds(groupId) : null,
                         memberCount:groupId ? FoxCanvasGroups.members(groupId).length : 0 };
            }""")
            assert created["count"] == 1, created
            assert created["groupId"], created
            assert created["memberCount"] == 2

            expected = page.evaluate(
                """ids => {
                    const nodeA = nodes.find(n => n.id === ids.a), nodeB = nodes.find(n => n.id === ids.b);
                    const sizeA = canvasEngine.nodeSize(nodeA), sizeB = canvasEngine.nodeSize(nodeB);
                    const x1 = Math.min(nodeA.x, nodeB.x), y1 = Math.min(nodeA.y, nodeB.y);
                    const x2 = Math.max(nodeA.x + sizeA.width, nodeB.x + sizeB.width);
                    const y2 = Math.max(nodeA.y + sizeA.height, nodeB.y + sizeB.height);
                    return { x1, y1, x2, y2 };
                }""",
                created,
            )
            bounds = created["bounds"]
            assert bounds["x"] == expected["x1"] - 20
            assert bounds["y"] == expected["y1"] - 32
            assert bounds["width"] == (expected["x2"] - expected["x1"]) + 40
            assert bounds["height"] == (expected["y2"] - expected["y1"]) + 52
            assert "组" in created["label"]

            # 容器随成员位移自动重新包裹（把左侧节点往左上拖，成员包围盒两轴都应外扩）
            before_move = created["bounds"]
            page.evaluate(
                """ids => { const node = nodes.find(n => n.id === ids.a); node.x -= 96; node.y -= 48; placeNode(node); }""",
                created,
            )
            page.wait_for_timeout(80)
            after_move = page.evaluate(
                "() => FoxCanvasGroups.bounds(document.querySelector('.group-box').dataset.group)"
            )
            assert after_move["x"] == before_move["x"] - 96
            assert after_move["y"] == before_move["y"] - 48
            assert after_move["width"] == before_move["width"] + 96
            assert after_move["height"] == before_move["height"] + 48

            # 把组框带进视野中心，再按组名标签拖动（Playwright 用真实坐标点击，元素必须在画布内）
            page.evaluate("""() => {
                const b = FoxCanvasGroups.bounds(document.querySelector('.group-box').dataset.group);
                fitRect(b.x - 60, b.y - 60, b.width + 120, b.height + 120);
            }""")
            page.wait_for_timeout(350)
            label_box = page.locator(".group-label").first.bounding_box()
            canvas_box = page.locator("#viewport").bounding_box()
            assert label_box["x"] > canvas_box["x"] and label_box["x"] + label_box["width"] < canvas_box["x"] + canvas_box["width"]
            assert label_box["y"] > canvas_box["y"] and label_box["y"] + label_box["height"] < canvas_box["y"] + canvas_box["height"]

            # 拖动组名标签 = 整组移动（容器本体不挡事件，工作区头部与节点交互不受影响）
            before = page.evaluate(
                "ids => [ids.a, ids.b].map(id => ({x:nodes.find(n => n.id === id).x, y:nodes.find(n => n.id === id).y}))",
                created,
            )
            page.mouse.move(label_box["x"] + label_box["width"] / 2, label_box["y"] + label_box["height"] / 2)
            page.mouse.down()
            page.mouse.move(
                label_box["x"] + label_box["width"] / 2 + 64,
                label_box["y"] + label_box["height"] / 2 + 40,
                steps=6,
            )
            page.mouse.up()
            after = page.evaluate(
                "ids => [ids.a, ids.b].map(id => ({x:nodes.find(n => n.id === id).x, y:nodes.find(n => n.id === id).y}))",
                created,
            )
            assert (after[0]["x"], after[0]["y"]) != (before[0]["x"], before[0]["y"]), (before, after)
            assert after[0]["x"] - before[0]["x"] == after[1]["x"] - before[1]["x"]
            assert after[0]["y"] - before[0]["y"] == after[1]["y"] - before[1]["y"]
            assert page.evaluate("selectedIds.size") == 2

            # 容器本体不吃事件：节点拖动、工作区头部按钮仍可命中
            passthrough = page.evaluate("""() => {
                const box = document.querySelector('.group-box');
                const rect = box.getBoundingClientRect();
                const point = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
                return { pointerEvents:getComputedStyle(box).pointerEvents, hitIsGroupBox:point === box,
                         labelPointerEvents:getComputedStyle(box.querySelector('.group-label')).pointerEvents };
            }""")
            assert passthrough == {"pointerEvents": "none", "hitIsGroupBox": False, "labelPointerEvents": "auto"}

            # 双击组名重命名
            page.once("dialog", lambda dialog: dialog.accept("像素小组"))
            page.locator(".group-label").first.dblclick()
            page.wait_for_timeout(150)
            assert "像素小组" in page.locator(".group-label").first.text_content()

            # 取消组合 → 容器消失
            page.evaluate("() => FoxCanvasProductivity.ungroupSelection()")
            page.wait_for_timeout(100)
            assert page.locator(".group-box").count() == 0
            assert page.evaluate("FoxCanvasGroups.list().length") == 0

            assert not errors
            browser.close()
