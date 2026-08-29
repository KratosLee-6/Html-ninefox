"""generate-screenshots.py · 一键生成 6 张 GitHub README 截图

用法：
    python assets/generate-screenshots.py
    python assets/generate-screenshots.py --only hero        # 只生成某一张
    python assets/generate-screenshots.py --only hero,cli-demo

依赖：
    pip install playwright
    playwright install chromium

输出：
    assets/screenshots/hero.png          (1600×900)
    assets/screenshots/cli-demo.png      (1200×800)
    assets/screenshots/5-style-compare.png (1600×900)
    assets/screenshots/workbench.png     (1440×900)
    assets/screenshots/sequence-diagram.png (1600×1000)
    assets/screenshots/output-example.png (1440×900)
"""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# ── 路径 ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent  # 07_GitHub开源发布/
SCREENSHOTS = ROOT / "assets" / "screenshots"
SCREENSHOTS.mkdir(parents=True, exist_ok=True)

CLI_DEMO = ROOT / "assets" / "cli-demo-interactive.html"
WORKBENCH = ROOT.parent / "03_Demo" / "demo-v1.html"
SEQUENCE = ROOT.parent / "04_架构图" / "htmlninefox-sequence.html"
OUTPUT_EXAMPLE = Path("C:/tmp/day10c/html9n-2026-08-29-151323/output.html")

# ── 6 张图配置 ──────────────────────────────────────────────────────
TARGETS = [
    {
        "file": "hero.png",
        "size": (1600, 900),
        "url": CLI_DEMO.as_uri(),
        "wait_ms": 1200,                      # 等 xterm 初始化
        "click_play": False,                  # 静态 hero — 不点 Play
        "desc": "Hero — 静态（play 之前）",
    },
    {
        "file": "cli-demo.png",
        "size": (1200, 800),
        "url": CLI_DEMO.as_uri(),
        "wait_ms": 1200,                      # 等 xterm 初始化
        "click_play": True,
        "speed": "2x",                        # 2x 速度跑 demo
        "play_offset_ms": 4500,               # 2x 后等 stage 3 (asset_expert @ 8000ms/2 = 4000ms)
        "desc": "CLI demo — 跑到 stage 3 (asset_expert)",
    },
    {
        "file": "5-style-compare.png",
        "size": (1600, 900),
        "url": CLI_DEMO.as_uri(),
        "wait_ms": 1200,
        "click_play": True,
        "speed": "2x",
        "play_offset_ms": 3300,               # 2x 后等 style_expert 阶段 (5100-7600ms / 2 = 2550-3800ms)
        "desc": "5-style compare — style_expert 4 candidate + winner",
    },
    {
        "file": "workbench.png",
        "size": (1440, 900),
        "url": WORKBENCH.as_uri(),
        "wait_ms": 2000,                      # 等字体/资源
        "click_play": False,
        "desc": "Workbench demo-v1 (5 板块)",
    },
    {
        "file": "sequence-diagram.png",
        "size": (1600, 1000),
        "url": SEQUENCE.as_uri(),
        "wait_ms": 3000,                      # archify SVG 渲染
        "click_play": False,
        "desc": "Sequence diagram — archify 渲染",
    },
    {
        "file": "output-example.png",
        "size": (1440, 900),
        "url": OUTPUT_EXAMPLE.as_uri(),
        "wait_ms": 1500,
        "click_play": False,
        "desc": "output.html (linear 风格示例)",
    },
]


def parse_only(only_arg: str | None) -> set[str] | None:
    """把 'hero,cli-demo' 转成 {'hero','cli-demo'} 集合；None 表示全跑。"""
    if not only_arg:
        return None
    return {x.strip() for x in only_arg.split(",") if x.strip()}


def generate_one(browser, target: dict) -> dict:
    """跑单张图；返回结果 dict。"""
    w, h = target["size"]
    page = browser.new_page(viewport={"width": w, "height": h})
    result = {"file": target["file"], "status": "ok", "size_kb": 0}

    try:
        page.goto(target["url"], wait_until="domcontentloaded", timeout=15000)

        if target["wait_ms"]:
            page.wait_for_timeout(target["wait_ms"])

        if target.get("click_play"):
            # 先设置速度（默认 1x；脚本里可选 2x/0.5x）
            speed = target.get("speed")
            if speed:
                try:
                    page.click(f'.speed-btn[data-speed="{speed.replace("x","")}"]', timeout=1500)
                except Exception:
                    pass  # 没找到就保持默认速度
            # 找到 #play-btn 触发 demo
            try:
                page.click("#play-btn", timeout=2000)
            except Exception:
                pass
            offset = target.get("play_offset_ms", 500)
            page.wait_for_timeout(offset)

        out_path = SCREENSHOTS / target["file"]
        page.screenshot(path=str(out_path), full_page=False)
        result["size_kb"] = out_path.stat().st_size // 1024
    except Exception as e:
        result["status"] = f"fail: {type(e).__name__}: {e}"
    finally:
        page.close()

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 6 张 GitHub README 截图")
    parser.add_argument("--only", help="只生成指定子集 (逗号分隔文件名不含扩展名)")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划不实际跑")
    args = parser.parse_args()

    only = parse_only(args.only)
    plan = [t for t in TARGETS if (only is None or Path(t["file"]).stem in only)]

    print(f"📸 生成 {len(plan)} 张截图")
    print(f"   输出目录: {SCREENSHOTS}")
    print()

    if args.dry_run:
        for t in plan:
            print(f"  · {t['file']:30s} {t['size'][0]}x{t['size'][1]}  {t['desc']}")
        return 0

    started = time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for t in plan:
                r = generate_one(browser, t)
                status = "✓" if r["status"] == "ok" else "✗"
                size = f"{r['size_kb']} KB" if r["status"] == "ok" else "—"
                w, h = t["size"]
                print(f"  {status} {t['file']:30s} {w}x{h}  ({size})  {r['status']}")
        finally:
            browser.close()

    elapsed = time.time() - started
    ok = sum(1 for t in plan if Path(SCREENSHOTS / t["file"]).exists())
    print()
    print(f"✅ Done · {ok}/{len(plan)} screenshots in {SCREENSHOTS}  ({elapsed:.1f}s)")
    return 0 if ok == len(plan) else 1


if __name__ == "__main__":
    sys.exit(main())