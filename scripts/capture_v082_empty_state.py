"""v0.8.2 证据截图：检查器空态与「写一句需求」面板。

跑法（先起服务）：
    .venv/Scripts/python.exe scripts/capture_v082_empty_state.py --base http://127.0.0.1:8620
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
        page.wait_for_function("window.FoxWorkbenchUI", timeout=30000)
        page.wait_for_timeout(800)

        page.evaluate("select(null)")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "inspector-empty-1440.png"))
        print("shot", "inspector-empty-1440.png")

        page.click('#inspector .ins-empty-actions [data-action="openCreatePanel"]')
        page.wait_for_timeout(600)
        page.screenshot(path=str(OUT / "create-panel-1440.png"))
        print("shot", "create-panel-1440.png")

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(args.base + "/")
        mobile.wait_for_function("window.FoxWorkbenchUI", timeout=30000)
        mobile.wait_for_timeout(700)
        mobile.evaluate("select(null)")
        mobile.wait_for_timeout(400)
        mobile.screenshot(path=str(OUT / "inspector-empty-390.png"))
        print("shot", "inspector-empty-390.png")

        browser.close()

    print("pageerror:", errors or "none")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
