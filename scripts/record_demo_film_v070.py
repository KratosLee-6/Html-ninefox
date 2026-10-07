"""Record the v0.7.0 page-decomposition session — every pixel from the live page.

与 record_demo_film.py 同一条纪律：界面画面必须录自真实运行的服务，
真实光标移动、真实逐字输入、真实等待；文生视频模型不得用于界面镜头
（H3 只出现在无文字的抽象片头，底版见 assets/promo/opener-h3-2k.mp4）。

v0.7.0 的主线换成了网页反向拆解：

  打开工作台 → 设计吸收 → 选 Google Fonts 源（内置两个开放许可源之一）
  → 逐字输入 https://example.com/ → 抓取为候选 → 审核台过目
  → 采纳为模板 → 拆块并生成（真实 API）→ 打开成品
  → 页面自己的正文出现在生成的落地页里 → 回到工作台看入库结果

运行前置（录制绝不污染真实项目）：
    python -m htmlninefox.cli serve --host 127.0.0.1 --port 8634 \
        --output .tmp/demo-run-v070
    python scripts/record_demo_film_v070.py

产物：.tmp/demo-run-video-v070/session.webm + events.json（给合成脚本排字幕）
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("FOX_DEMO_BASE_V070", "http://127.0.0.1:8634")
OUT = ROOT / ".tmp/demo-run-video-v070"
URL = "https://example.com/"
W, H = 1920, 1080

BEAT = {
    "load": 2.4,
    "to_intake": 1.1,
    "open_panel": 2.2,
    "to_url": 0.9,
    "type": 0.09,
    "after_type": 1.4,
    "to_source": 0.9,
    "after_source": 1.2,
    "to_fetch": 0.9,
    "fetch_wait": 4.0,
    "read_candidate": 3.4,
    "to_adopt": 1.0,
    "adopt_wait": 2.6,
    "read_adopted": 2.6,
    "to_approved_tab": 1.0,
    "read_approved": 2.4,
    "generate_wait": 5.0,
    "output_load": 2.0,
    "scroll_steps": 5,
    "scroll_beat": 1.5,
    "read_output_tail": 2.4,
    "back_home": 2.0,
    "read_sidebar": 3.0,
    "outro": 2.2,
}


class Events:
    def __init__(self) -> None:
        self.t0 = time.time()
        self.items: list[dict] = []

    def mark(self, key: str, caption: str) -> float:
        t = time.time() - self.t0
        self.items.append({"key": key, "t": round(t, 2), "caption": caption})
        log(f"{key} @ {t:.1f}s")
        return t


def log(msg: str) -> None:
    print(f"  [{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def visible_box(page, selector: str) -> dict:
    """页面里同名按钮可能有多份（桌面/移动），挑第一个可见的拿坐标。"""
    boxes = page.eval_on_selector_all(
        selector,
        "els => els.filter(e => e.offsetParent !== null).map("
        "e => { const r = e.getBoundingClientRect();"
        " return {x: r.x + r.width/2, y: r.y + r.height/2}; })")
    if not boxes:
        raise SystemExit(f"no visible element for {selector}")
    return boxes[0]


def move_to(page, selector: str) -> None:
    box = visible_box(page, selector)
    page.mouse.move(box["x"] * 0.62, box["y"] * 0.72)
    page.wait_for_timeout(220)
    page.mouse.move(box["x"], box["y"], steps=18)
    page.wait_for_timeout(260)


def click_at(page, selector: str) -> None:
    """真实鼠标按下：先 move_to 拖出可见轨迹，再在元素中心点击。"""
    box = visible_box(page, selector)
    page.mouse.move(box["x"], box["y"], steps=8)
    page.wait_for_timeout(160)
    page.mouse.click(box["x"], box["y"])


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    ev = Events()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--force-device-scale-factor=1"])
        ctx = browser.new_context(
            viewport={"width": W, "height": H},
            record_video_dir=str(OUT),
            record_video_size={"width": W, "height": H},
            device_scale_factor=1)
        page = ctx.new_page()
        page.set_default_timeout(30000)

        # ---- 1. 工作台打开（顶栏 v0.7.0）
        log("opening workbench")
        page.goto(BASE, wait_until="networkidle")
        assert page.inner_text("#ver").strip() == "v0.7.0", "顶栏版本必须是 v0.7.0"
        ev.mark("load", "Html九尾狐 v0.7.0 · 开工第一天")
        page.wait_for_timeout(int(BEAT["load"] * 1000))

        # ---- 2. 打开顶栏「⋯」菜单 → 设计吸收（菜单弹层 z-index 140，可正常点击）
        log("cursor to ⋯ menu")
        move_to(page, "details.topbar-more > summary")
        click_at(page, "details.topbar-more > summary")
        page.wait_for_selector("details.topbar-more[open]", timeout=10000)
        page.wait_for_timeout(500)
        log("cursor to 设计吸收")
        move_to(page, "button[onclick=\"openIntake()\"]")
        click_at(page, "button[onclick=\"openIntake()\"]")
        page.wait_for_selector("#intake-modal:not([hidden])")
        ev.mark("intake_open", "设计吸收 · 安全抓取 · 审核后入库")
        page.wait_for_timeout(int(BEAT["open_panel"] * 1000))

        # ---- 3. 逐字输入网址（内置开放许可源：Google Fonts）
        move_to(page, "#intake-fetch-url")
        click_at(page, "#intake-fetch-url")
        log(f"typing {URL}")
        page.keyboard.type(URL, delay=int(BEAT["type"] * 1000))
        assert page.input_value("#intake-fetch-url") == URL
        ev.mark("typed", "贴一个公开网址：example.com")
        page.wait_for_timeout(int(BEAT["after_type"] * 1000))

        move_to(page, "#intake-source")
        page.select_option("#intake-source", "google-fonts")
        ev.mark("source", "来源：Google Fonts · 开放许可（正文可随行）")
        page.wait_for_timeout(int(BEAT["after_source"] * 1000))

        # ---- 4. 真实抓取
        move_to(page, "#intake-fetch-btn")
        click_at(page, "#intake-fetch-btn")
        # 成功提示走 flash()（时间线状态），这里直接等候选卡出现在列表里
        page.wait_for_selector("#intake-list button.btn-primary", timeout=45000)
        ev.mark("fetched", "抓回来，先落审核台等你过目")
        page.wait_for_timeout(int(BEAT["fetch_wait"] * 1000))

        # ---- 5. 审核台过目（候选带开放许可标签）
        page.wait_for_selector("#intake-list .btn-primary", timeout=15000)
        title = page.eval_on_selector(
            "#intake-list", "e => e.textContent.includes('Example Domain')")
        assert title, "候选里没有 Example Domain"
        ev.mark("candidate", "候选带许可标签 · 采纳前先看清楚")
        page.wait_for_timeout(int(BEAT["read_candidate"] * 1000))

        # ---- 6. 采纳
        move_to(page, "#intake-list button.btn-primary")
        click_at(page, "#intake-list button.btn-primary")
        # 采纳提示走 flash()；等已采纳候选在服务端真实出现
        page.wait_for_function(
            "async () => { const r = await (await fetch('/api/intake/candidates?status=approved')).json();"
            " return r.candidates && r.candidates.length > 0; }", timeout=30000)
        ev.mark("adopted", "采纳 → 整页入模板库，分块可以进生成")
        page.wait_for_timeout(int(BEAT["adopt_wait"] * 1000))
        click_at(page, "[data-intake-filter='approved']")
        page.wait_for_timeout(int(BEAT["read_approved"] * 1000))
        ev.mark("approved_tab", "已采纳 · REAL HTML 模板")
        page.wait_for_timeout(600)

        # ---- 7. 拆块并生成（真实 API；画面在此处停一拍，字幕交代）
        log("page-blocks + generate (real API)")
        result = page.evaluate(
            """
            async () => {
              const cands = await (await fetch('/api/intake/candidates?status=approved')).json();
              const cid = cands.candidates[0].candidate_id;
              const pb = await (await fetch('/api/intake/page-blocks', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({candidate_id: cid})})).json();
              const gen = await (await fetch('/api/generate', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({prompt: '做一个产品介绍落地页，品牌「Example」',
                                      intent: 'landing', quiet_llm: true,
                                      blocks: pb.blocks})})).json();
              return gen;
            }
            """
        )
        assert result.get("ok") is True, f"generate failed: {result}"
        preview = result["preview_url"]
        ev.mark("generating", "拆成分区，生成时页面正文真的跟过来")
        page.wait_for_timeout(int(BEAT["generate_wait"] * 1000))

        # ---- 8. 打开成品，慢慢滚过页面自己的正文
        log(f"opening output {preview}")
        page.goto(BASE + preview, wait_until="networkidle")
        page.wait_for_timeout(int(BEAT["output_load"] * 1000))
        ev.mark("output", "成品 · 页面自己的标题与正文出现在这里")
        for i in range(BEAT["scroll_steps"]):
            page.mouse.wheel(0, 420)
            page.wait_for_timeout(int(BEAT["scroll_beat"] * 1000))
            if i == 1:
                ev.mark("output_scroll", "不是只借布局——正文一字不差带过来了")
        ev.mark("output_tail", "落地页 / 看板 / 幻灯片 / 海报 / 架构图 / 文档，六类都能吃")
        page.wait_for_timeout(int(BEAT["read_output_tail"] * 1000))

        # ---- 9. 回工作台，看入库结果
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(int(BEAT["back_home"] * 1000))
        ev.mark("home", "采纳的页面已在侧栏 REAL HTML 模板库")
        page.wait_for_timeout(int(BEAT["read_sidebar"] * 1000))
        ev.mark("outro", "GitHub: KratosLee-6/Html-ninefox · v0.7.0")
        page.wait_for_timeout(int(BEAT["outro"] * 1000))

        page.wait_for_timeout(800)
        ctx.close()
        browser.close()

    (OUT / "events.json").write_text(
        json.dumps({"events": ev.items, "duration": time.time() - ev.t0},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    vids = sorted(OUT.glob("*.webm"))
    if not vids:
        raise SystemExit("no video produced")
    dst = OUT / "session.webm"
    vids[0].rename(dst)
    print(f"\nrecorded: {dst}  {dst.stat().st_size/1024/1024:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
