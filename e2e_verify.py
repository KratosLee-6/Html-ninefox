"""e2e_verify.py · 发布验收：生成 5 类内容 + 反馈迭代 + Web 工作台截图

运行：python e2e_verify.py
输出：e2e-shots/*.png + 控制台验收结果
"""

from __future__ import annotations

import asyncio
import sys
import threading
import time
from pathlib import Path

from htmlninefox import __version__, pipeline
from htmlninefox.server import app as server_app

HERE = Path(__file__).resolve().parent
SHOTS = HERE / "e2e-shots"
SHOTS.mkdir(exist_ok=True)
OUT = HERE / "e2e-output"

PROMPTS = [
    ("landing", "做一个 SaaS 落地页，品牌「狐构」，主推 AI 创作工具，目标用户是设计师"),
    ("dashboard", "做一个运营数据看板，深色，展示订单和KPI"),
    ("deck", "做一个发布会 PPT，主题是 AI-native 创作工具狐构"),
    ("poster", "设计一张活动宣传海报，鲜艳活力"),
    ("archdoc", "写一份狐构技术方案文档，包含架构图"),
]

results = []


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, ok, detail))
    print(f"[{'✓' if ok else '✗'}] {name}" + (f"  {detail}" if detail else ""))


def start_server(output_root: Path, port=8640):
    output_root.mkdir(parents=True, exist_ok=True)
    server_app._OUTPUT_ROOT = output_root
    from htmlninefox.server.app import ThreadingHTTPServer, _Handler
    srv = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{port}", srv


async def main():
    # ---------- 1. CLI 流水线：5 类内容 ----------
    outputs = {}
    for intent, prompt in PROMPTS:
        r = pipeline.run_expert(prompt, output=str(OUT), quiet_llm=True)
        outputs[intent] = r["work"]
        html = (r["work"] / "output.html").read_text(encoding="utf-8")
        check(f"生成 {intent}", html.startswith("<!doctype html>") and len(html) > 3000,
              f"{len(html)}B · {r['preset_id']} · {r['route_decision']}")

    # ---------- 2. 反馈迭代（真实变化）----------
    work = outputs["landing"]
    before = (work / "output.html").read_text(encoding="utf-8")
    fb = pipeline.run_feedback(str(work), "颜色再深一点，标题大一点", revise=True)
    after = (work / "output.html").read_text(encoding="utf-8")
    check("反馈迭代 rev1", fb.get("ok") and before != after,
          f"rules={fb.get('applied_rules')}")
    fb2 = pipeline.run_feedback(str(work), "参考 vercel", revise=True)
    check("反馈迭代 rev2（参考预设切换）", fb2.get("ok") and fb2.get("revision") == 2)

    # ---------- 3. Playwright 截图 ----------
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()

        for intent, _ in PROMPTS:
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.goto((outputs[intent] / "output.html").as_uri())
            await page.wait_for_timeout(600)
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            await page.screenshot(path=SHOTS / f"{intent}.png")
            check(f"截图 {intent}", not errors and (SHOTS / f"{intent}.png").exists())
            await page.close()

        # deck 翻页交互验证
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto((outputs["deck"] / "output.html").as_uri())
        await page.keyboard.press("ArrowRight")
        await page.wait_for_timeout(600)
        cur = await page.text_content("#cur")
        check("deck 翻页交互", cur and cur.strip() == "2", f"page={cur}")
        await page.screenshot(path=SHOTS / "deck-page2.png")
        await page.close()

        # 无限画布工作台 UI（使用隔离输出目录，不读取或覆盖用户快照）
        base, srv = start_server(OUT / f"workbench-{time.time_ns()}")
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        page_errors = []
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        try:
            await page.goto(base + "/")
            await page.wait_for_timeout(1600)
            kinds = await page.evaluate("nodes.map(node => node.kind)")
            seeded = kinds.count("ws") == 1 and kinds.count("requirement") == 1
            nav_count = await page.locator(".workspace-nav-item").count()
            check("工作区列表与预置场景", seeded and nav_count == 1, f"kinds={kinds}")

            point = await page.evaluate("""() => {
                const ws = nodes.find(node => node.kind === 'ws');
                const rect = viewport.getBoundingClientRect();
                return {
                    x: Math.min(rect.right - 80, rect.left + camera.x + (ws.x + ws.w - 110) * camera.z),
                    y: Math.min(rect.bottom - 80, rect.top + camera.y + (ws.y + ws.h - 90) * camera.z),
                };
            }""")
            before = await page.evaluate("""() => {
                const ws=nodes.find(node=>node.kind==='ws'), req=nodes.find(node=>node.kind==='requirement');
                return {wx:ws.x, wy:ws.y, rx:req.x, ry:req.y};
            }""")
            await page.mouse.move(point["x"], point["y"])
            await page.mouse.down()
            await page.mouse.move(point["x"] + 96, point["y"] + 64, steps=8)
            await page.mouse.up()
            after = await page.evaluate("""() => {
                const ws=nodes.find(node=>node.kind==='ws'), req=nodes.find(node=>node.kind==='requirement');
                return {wx:ws.x, wy:ws.y, rx:req.x, ry:req.y};
            }""")
            dx, dy = after["wx"] - before["wx"], after["wy"] - before["wy"]
            moved_together = dx != 0 and dy != 0 and after["rx"] - before["rx"] == dx and after["ry"] - before["ry"] == dy
            check("工作区整体拖动", moved_together, f"delta=({dx},{dy})")

            await page.locator(".workspace-nav-edit").first.click()
            await page.fill("#workspace-name", "品牌官网工作区")
            await page.locator(".workspace-color").nth(2).click()
            renamed = await page.evaluate("nodes.find(node=>node.kind==='ws').title")
            color = await page.evaluate("nodes.find(node=>node.kind==='ws').data.color")
            check("工作区重命名与颜色", renamed == "品牌官网工作区" and color == "#E07A3F", f"{renamed} · {color}")

            await page.click(".workspace-add")
            nav_count = await page.locator(".workspace-nav-item").count()
            status = await page.text_content("#tl-status")
            check("多工作区导航与独立进度", nav_count == 2 and "0 素材" in (status or ""), f"nav={nav_count} · {status}")

            templates = await page.evaluate("fetch('/api/templates').then(response=>response.json()).then(data=>data.items)")
            ids = {item["id"] for item in templates}
            required = {"fox-pixel-garden", "fox-duotone-studio", "fox-editorial-ink", "fox-swiss-signal", "fox-soft-silver"}
            check("11 套真实视觉系统", len(templates) >= 11 and required <= ids, f"templates={len(templates)}")
            await page.click('.tab[data-tab="styles"]')
            await page.wait_for_timeout(900)
            theme_before = await page.get_attribute("html", "data-theme")
            await page.click("#btn-theme")
            theme_after = await page.get_attribute("html", "data-theme")
            stored_theme = await page.evaluate("localStorage.getItem('fox-ui-theme')")
            check("像素花园双主题", theme_before == "pixel-paper" and theme_after == "pixel-night" and stored_theme == "pixel-night", f"{theme_before} -> {theme_after}")
            await page.screenshot(path=SHOTS / f"workbench-v{__version__}-night.png")
            await page.click("#btn-theme")
            await page.screenshot(path=SHOTS / f"workbench-v{__version__}-paper.png")
            check("工作台无 JS 错误", not page_errors, "; ".join(page_errors[:3]))
        finally:
            srv.shutdown()
            srv.server_close()
        await browser.close()

    # ---------- 汇总 ----------
    fails = [r for r in results if not r[1]]
    print(f"\n{'=' * 50}\n验收结果：{len(results) - len(fails)}/{len(results)} 通过")
    if fails:
        for name, _, detail in fails:
            print(f"  ✗ {name}  {detail}")
        sys.exit(1)
    print("全部通过 ✅")


if __name__ == "__main__":
    asyncio.run(main())
