"""v0.8.2 证据截图：工作台外壳在 token 收敛后的状态。

跑法（先起服务：python -c "from htmlninefox.cli import main; main()" serve --port 8620）：
    .venv/Scripts/python.exe scripts/capture_v082_shell.py --base http://127.0.0.1:8620
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "screenshots" / "v0.8.2"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8620")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.base + "/")
        page.add_style_tag(content=".toast-region{display:none !important}")
        page.wait_for_function("window.FoxWorkbenchUI", timeout=30000)
        page.wait_for_timeout(900)

        for theme in ("pixel-paper", "pixel-night"):
            page.evaluate(f"document.documentElement.dataset.theme = '{theme}'")
            page.wait_for_timeout(400)
            page.screenshot(path=str(OUT / f"workbench-{theme}-1440.png"))
            print("shot", f"workbench-{theme}-1440.png")

        page.evaluate("document.documentElement.dataset.theme = 'pixel-paper'")
        page.wait_for_timeout(300)
        page.evaluate("window.FoxIntake.open()")
        page.wait_for_timeout(700)
        page.screenshot(path=str(OUT / "intake-desk-1440.png"))
        print("shot intake-desk-1440.png")
        page.evaluate("window.FoxIntake.close()")

        page.evaluate("window.FoxExports && window.FoxExports.open ? window.FoxExports.open() : null")
        page.wait_for_timeout(700)
        page.screenshot(path=str(OUT / "export-centre-1440.png"))
        print("shot export-centre-1440.png")

        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "workbench-mobile-390.png"))
        print("shot workbench-mobile-390.png")

        print("pageerror:", errors or "none")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
