"""canvas_e2e.py · v0.5 工作区编排、真实预览、磁吸连线与推进流水线验收。"""

import asyncio
import json
import sys
import tempfile
import threading
from pathlib import Path

from htmlninefox import __version__
from htmlninefox.server import app as server_app

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
TEST_OUTPUT = Path(tempfile.mkdtemp(prefix="htmlninefox-canvas-e2e-"))
RELEASE_SHOTS = HERE / "assets" / "screenshots" / f"v{__version__}"
RELEASE_SHOTS.mkdir(parents=True, exist_ok=True)


def start_server():
    TEST_OUTPUT.mkdir(parents=True, exist_ok=True)
    server_app._OUTPUT_ROOT = TEST_OUTPUT
    server = server_app.ThreadingHTTPServer(("127.0.0.1", 0), server_app._Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://127.0.0.1:{server.server_port}", server, thread


BASE, SERVER, SERVER_THREAD = start_server()
SHOTS = "e2e-shots"
results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        await page.add_init_script("localStorage.clear()")
        await page.goto(BASE + "/")
        await page.wait_for_function("window.FoxCanvasProductivity && nodes.length >= 5", timeout=15000)
        await page.wait_for_timeout(300)

        # 1. 预置场景：工作区 + 需求 + 版式 + 风格 + 内容块
        kinds = await page.evaluate("nodes.map(n => n.kind)")
        check("预置工作区编排", kinds.count("ws") == 1 and kinds.count("requirement") == 1
              and kinds.count("template") == 1 and kinds.count("style") == 1
              and kinds.count("block") == 1, str(kinds))

        # 2. 卡片主体拖动（v0.4 修复：任意非交互区域可拖）
        pos0 = await page.evaluate(
            "JSON.stringify({x:nodes.find(n=>n.kind==='requirement').x, y:nodes.find(n=>n.kind==='requirement').y})")
        bb = await page.locator(".node.requirement .node-body, #node-2 .node-body").first.bounding_box()
        await page.mouse.move(bb["x"] + 15, bb["y"] + 4)
        await page.mouse.down()
        await page.mouse.move(bb["x"] + 150, bb["y"] + 80, steps=6)
        await page.mouse.up()
        pos1 = await page.evaluate(
            "JSON.stringify({x:nodes.find(n=>n.kind==='requirement').x, y:nodes.find(n=>n.kind==='requirement').y})")
        check("卡片主体可拖动（修复验证）", pos0 != pos1, f"{pos0} → {pos1}")

        # 3. 工作区头栏拖动（头栏已移入框内，不再被顶栏遮挡）
        ws0 = await page.evaluate(
            "JSON.stringify({x:nodes.find(n=>n.kind==='ws').x, y:nodes.find(n=>n.kind==='ws').y})")
        wb = await page.locator(".ws-head").first.bounding_box()
        await page.mouse.move(wb["x"] + 30, min(wb["y"] + 12, 800))
        await page.mouse.down()
        await page.mouse.move(wb["x"] + 130, wb["y"] + 60, steps=6)
        await page.mouse.up()
        ws1 = await page.evaluate(
            "JSON.stringify({x:nodes.find(n=>n.kind==='ws').x, y:nodes.find(n=>n.kind==='ws').y})")
        check("工作区头栏可拖动", ws0 != ws1, f"{ws0} → {ws1}")

        # 4. 素材库真实预览：版式/风格直接渲染 HTML，内容块继续线框化
        await page.click('.tab[data-tab="blocks"]')
        n_mini = await page.evaluate("document.querySelectorAll('#pal .mini').length")
        await page.click('.tab[data-tab="layouts"]')
        await page.wait_for_timeout(500)
        n_layout_preview = await page.evaluate("document.querySelectorAll('#pal .template-thumb iframe').length")
        await page.locator('#pal .preview-open').first.click()
        await page.wait_for_timeout(250)
        modal_preview = await page.evaluate("!document.querySelector('#preview-modal').hidden && (document.querySelector('#preview-frame').src.includes('/api/template-preview') || document.querySelector('#preview-frame').src.includes('/api/gallery-preview'))")
        await page.click('#preview-close')
        await page.click('.tab[data-tab="styles"]')
        await page.wait_for_timeout(500)
        n_style_preview = await page.evaluate("document.querySelectorAll('#pal .template-thumb iframe').length")
        style_node_preview = await page.evaluate("document.querySelector('.node.style [data-style-frame]').src.includes('/api/template-preview')")
        check("素材库真实 HTML 预览",
              n_mini >= 12 and n_layout_preview >= 6 and n_style_preview >= 6 and modal_preview and style_node_preview,
              f"blocks={n_mini} layouts={n_layout_preview} styles={n_style_preview}")

        # 5. 缩放状态下吸附与端口连线
        snap_ok = await page.evaluate("""() => {
            camera = {x:90,y:70,z:1.25}; applyCamera(false); drawEdges();
            const req=nodes.find(n=>n.kind==='requirement'), tpl=nodes.find(n=>n.kind==='template');
            const result=canvasEngine.snapNode(req,tpl.x+3,req.y,false);
            return result.x===tpl.x && result.guideX===tpl.x;
        }""")
        block_id = await page.evaluate("nodes.find(n=>n.kind==='block').id")
        template_id = await page.evaluate("nodes.find(n=>n.kind==='template').id")
        await page.evaluate("""([sourceId,targetId]) => {
            const source = nodes.find(node => node.id === sourceId);
            const target = nodes.find(node => node.id === targetId);
            const x1 = Math.min(source.x, target.x);
            const y1 = Math.min(source.y, target.y);
            const x2 = Math.max(source.x + canvasEngine.nodeSize(source).width, target.x + canvasEngine.nodeSize(target).width);
            const y2 = Math.max(source.y + canvasEngine.nodeSize(source).height, target.y + canvasEngine.nodeSize(target).height);
            fitRect(x1, y1, x2 - x1, y2 - y1, 180);
        }""", [block_id, template_id])
        await page.wait_for_timeout(120)
        source = await page.locator(f'#node-{block_id} .port-out').bounding_box()
        target = await page.locator(f'#node-{template_id} .port-in').bounding_box()
        before_edges = await page.evaluate("edges.length")
        await page.mouse.move(source['x']+source['width']/2, source['y']+source['height']/2)
        await page.mouse.down()
        await page.mouse.move(target['x']+target['width']/2, target['y']+target['height']/2, steps=12)
        await page.wait_for_timeout(80)
        highlighted = await page.locator(f'#node-{template_id} .port-in').evaluate("el=>el.classList.contains('link-target')")
        await page.mouse.up()
        connected = await page.evaluate("([a,b])=>edges.some(e=>e.from===a&&e.to===b)",[block_id,template_id])
        check("缩放后吸附与端口连线", snap_ok and highlighted and connected,
              f"snap={snap_ok} highlighted={highlighted} edges={before_edges}->{await page.evaluate('edges.length')}")

        # 3. 拖入色卡到工作区（HTML5 DnD 模拟 → 落点吸附）
        await page.click('.tab[data-tab="styles"]')
        await page.wait_for_timeout(300)
        await page.evaluate("""() => {
            const cards = [...document.querySelectorAll('#pal .pal-card')];
            const card = cards.find(c => c.dataset.pid.startsWith('color-'));
            const dt = new DataTransfer();
            card.dispatchEvent(new DragEvent('dragstart', { dataTransfer: dt, bubbles: true }));
            const ws = nodes.find(n => n.kind === 'ws');
            const [sx, sy] = [ws.x + ws.w - 200, ws.y + ws.h - 120];
            const vx = sx * camera.z + camera.x + document.getElementById('viewport').getBoundingClientRect().left;
            const vy = sy * camera.z + camera.y + document.getElementById('viewport').getBoundingClientRect().top;
            vp = document.getElementById('viewport');
            vp.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, clientX: vx, clientY: vy }));
        }""")
        await page.wait_for_timeout(300)
        has_color = await page.evaluate("nodes.some(n => n.kind === 'color')")
        check("色卡拖入工作区（落点吸附）", has_color)

        # 4. 推进流水线：拆解 → 组合 → 产物
        await page.click("#btn-go")
        try:
            await page.wait_for_function(
                "nodes.some(n => n.kind === 'output') && nodes.find(n => n.kind==='requirement').data.analysis",
                timeout=90000)
            ok = True
        except Exception:
            ok = False
        out = await page.evaluate("nodes.find(n => n.kind === 'output') || null")
        an = await page.evaluate("nodes.find(n => n.kind === 'requirement').data.analysis || null")
        check("推进：需求自动拆解", ok and an and an.get("intent"), f"intent={an and an.get('intent')} tone={an and an.get('tone')}")
        check("推进：自动组合生成产物", ok and out is not None,
              f"preset={out and out['data'].get('preset_id')} route={out and out['data'].get('project_name')}")
        edge_req_out = await page.evaluate(
            "edges.some(e => e.from === nodes.find(n=>n.kind==='requirement').id && e.to === (nodes.find(n=>n.kind==='output')||{}).id)")
        check("需求 → 产物 自动连线", edge_req_out)

        recipe = await page.evaluate("nodes.find(n => n.id === selected)?.data.recipe_run || null")
        check("Recipe Run 五阶段完成", recipe and recipe.get("status") == "succeeded"
              and len(recipe.get("stages", [])) == 5
              and all(stage.get("status") == "succeeded" for stage in recipe["stages"]),
              str([(stage.get("id"), stage.get("duration_ms")) for stage in (recipe or {}).get("stages", [])]))
        stage_count = await page.locator("#recipe-run-live .recipe-stage").count()
        check("产物检查器显示运行详情", stage_count == 5, f"stages={stage_count}")
        await page.evaluate("document.querySelectorAll('.fox-toast').forEach(item => item.remove())")
        await page.screenshot(path=RELEASE_SHOTS / "recipe-run.png")

        previous_run_id = recipe.get("id")
        await page.locator(".recipe-stage", has_text="质量验证").locator("button").click()
        await page.wait_for_function(
            """previous => {
              const run = nodes.find(n => n.id === selected)?.data.recipe_run;
              return run && run.id !== previous && run.status === 'succeeded' && run.rerun_from === 'verify';
            }""", arg=previous_run_id, timeout=30000)
        rerun = await page.evaluate("nodes.find(n => n.id === selected).data.recipe_run")
        check("质量验证可局部重跑", rerun.get("parent_run_id") == previous_run_id,
              f"{previous_run_id} → {rerun.get('id')}")
        await page.wait_for_timeout(2500)
        await page.screenshot(path=f"{SHOTS}/ws-advanced.png")

        # 5. 自动缩放（推进后 fitRect 生效）
        z = await page.evaluate("camera.z")
        check("自动缩放（适配工作区+产物）", 0.3 <= z <= 1.5, f"z={round(z, 3)}")

        # 6. 反馈迭代
        await page.fill("#fb-note", "颜色再深一点，标题大一点")
        await page.click("#fb-send")
        try:
            await page.wait_for_function(
                "nodes.find(n => n.kind === 'output')?.data.revision >= 1", timeout=60000)
            ok = True
        except Exception:
            ok = False
        rev = await page.evaluate("nodes.find(n => n.kind === 'output')?.data.revision")
        check("产物反馈迭代", ok and rev and rev >= 1, f"rev{rev}")
        await page.wait_for_timeout(1800)
        await page.screenshot(path=f"{SHOTS}/ws-feedback.png")

        # 7. 工作区 ⤢ 适配按钮 + 持久化
        await page.evaluate("camera = {x:0,y:0,z:1}; applyCamera();")
        await page.evaluate("fitWs(nodes.find(n => n.kind === 'ws').id)")
        z2 = await page.evaluate("camera.z")
        check("工作区 ⤢ 自动适配", 0.3 <= z2 <= 1.5, f"z={round(z2, 3)}")
        await page.reload()
        await page.wait_for_timeout(1500)
        n_all = await page.evaluate("nodes.length")
        check("画布状态持久化", n_all >= 6, f"nodes={n_all}")

        check("无页面 JS 错误", not errors, "; ".join(errors[:3]))
        await browser.close()

    fails = [r for r in results if not r[1]]
    print(f"\n{'=' * 46}\n工作区验收：{len(results) - len(fails)}/{len(results)} 通过")
    sys.exit(1 if fails else 0)


try:
    asyncio.run(main())
finally:
    SERVER.shutdown()
    SERVER.server_close()
    SERVER_THREAD.join(timeout=2)
