"""实拍一张不含客户文档、且节点不重叠的工作台界面（X 宣传用）。

与 capture_core_shots.py 的区别：那个脚本只 fitAll() 就拍，种子状态里
「产物」节点压在「风格」节点上，拍出来像 bug；这里先把产物节点拖开，
再拍。输出的图不写进 assets/screenshots/vX/（那是发版证据目录），
写到 assets/screenshots/x-promo/。

    .venv/Scripts/python.exe scripts/capture_x_workbench.py
"""
from __future__ import annotations

import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402

PORT = 8661
BASE = f"http://127.0.0.1:{PORT}"
OUT = ROOT / "assets" / "screenshots" / "x-promo"


def main() -> int:
    from htmlninefox.server import app as server_app

    out_root = ROOT / ".tmp" / "x-promo-projects"
    out_root.mkdir(parents=True, exist_ok=True)
    server_app._OUTPUT_ROOT = out_root

    srv = ThreadingHTTPServer(("127.0.0.1", PORT), server_app._Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.6)
    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(1800)

        page.evaluate("() => document.querySelectorAll('.fox-toast').forEach(t => t.remove())")

        nodes = page.evaluate("""() => [...document.querySelectorAll('.node')].map(n => {
            const r = n.getBoundingClientRect();
            return {cls: n.className, text: (n.innerText || '').slice(0, 24).replace(/\\n/g, ' '),
                    x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)};
        })""")
        print("节点：")
        for n in nodes:
            print("  ", n)

        # 找「产物」节点（文本里带 交付说明 / 产物），把它拖到画布右下空白处
        target = next((n for n in nodes if "交付说明" in n["text"] or "产物" in n["text"]), None)
        if target:
            # 其它节点的最右/最下，作为落点参考
            others = [n for n in nodes if n is not target]
            right = max((n["x"] + n["w"] for n in others), default=target["x"])
            bottom = max((n["y"] + n["h"] for n in others), default=target["y"])
            sx = target["x"] + min(120, target["w"] // 3)
            sy = target["y"] + 14
            tx = max(right + 70, target["x"] + 260)
            ty = min(bottom + 40, 700)
            print(f"拖动产物节点 ({sx},{sy}) -> ({tx},{ty})")
            page.mouse.move(sx, sy)
            page.mouse.down()
            page.mouse.move(tx, ty, steps=25)
            page.mouse.up()
            page.wait_for_timeout(700)

        page.evaluate("fitAll()")
        page.wait_for_timeout(900)
        page.evaluate("() => document.querySelectorAll('.fox-toast').forEach(t => t.remove())")

        shot = OUT / "workbench-x-1440.png"
        page.screenshot(path=str(shot))
        print(f"✓ {shot}  {shot.stat().st_size // 1024} KB")

        # 第二版：选中「风格」节点，让右侧检查器显示真实属性（空提示看起来像没数据）
        style = next((n for n in nodes if "风格" in n["text"]), None)
        if style:
            page.mouse.click(style["x"] + style["w"] // 2, style["y"] + 18)
            page.wait_for_timeout(700)
            page.evaluate("() => document.querySelectorAll('.fox-toast').forEach(t => t.remove())")
            shot2 = OUT / "workbench-x-1440-selected.png"
            page.screenshot(path=str(shot2))
            print(f"✓ {shot2}  {shot2.stat().st_size // 1024} KB")

        after = page.evaluate("""() => [...document.querySelectorAll('.node')].map(n => {
            const r = n.getBoundingClientRect();
            return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)];
        })""")
        print("拖后节点框：", after)
        browser.close()

    srv.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
