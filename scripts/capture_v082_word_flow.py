"""v0.8.2 实机验收：在真实服务上跑一遍 Word 导入 → 采纳 → 产物。

与 v0.8.1 的 capture 不同，这里打的是**已经跑着的**服务（默认 8620），
用的是脱敏示例文档（星野智造／栖木云），证据落 assets/screenshots/v0.8.2/。

    .venv/Scripts/python.exe scripts/capture_v082_word_flow.py --base http://127.0.0.1:8620
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.fixtures.demo_docx import build_plan_docx  # noqa: E402

OUT = ROOT / "assets" / "screenshots" / "v0.8.2"
DOCX = build_plan_docx(Path(tempfile.gettempdir()) / "fox082" / "demo-plan-flow.docx")


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
        page.wait_for_function("window.FoxDocx && window.FoxIntake", timeout=30000)

        page.evaluate("window.FoxIntake.open()")
        page.set_input_files("#docx-file", str(DOCX))
        page.click("#docx-analyze")
        page.wait_for_selector("#docx-proposal:not([hidden])", timeout=30000)
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "word-desk-proposal-1440.png"))
        page.select_option("#docx-intent", "doc")
        page.wait_for_timeout(300)
        page.click("#docx-adopt")
        page.wait_for_selector("#docx-result:not([hidden])", timeout=120000)
        href = page.get_attribute("#docx-result", "href")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "word-desk-adopted-1440.png"))

        page.goto(args.base + href)
        page.wait_for_timeout(700)
        page.screenshot(path=str(OUT / "word-artifact-doc-1440.png"))
        print("doc artifact:", href)

        # 换成 deck：同一份文档，换形态不换内容
        page.goto(args.base + "/")
        page.wait_for_function("window.FoxDocx && window.FoxIntake", timeout=30000)
        page.evaluate("window.FoxIntake.open()")
        page.set_input_files("#docx-file", str(DOCX))
        page.click("#docx-analyze")
        page.wait_for_selector("#docx-proposal:not([hidden])", timeout=30000)
        page.select_option("#docx-intent", "deck")
        page.click("#docx-adopt")
        page.wait_for_selector("#docx-result:not([hidden])", timeout=120000)
        deck = page.get_attribute("#docx-result", "href")
        page.goto(args.base + deck)
        page.wait_for_timeout(700)
        page.screenshot(path=str(OUT / "word-artifact-deck-1440.png"))
        print("deck artifact:", deck)
        print("pageerror:", errors or "none")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
