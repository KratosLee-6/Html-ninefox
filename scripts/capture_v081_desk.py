"""Capture the v0.8.1 Word desk: proposal state and the adopted artifact."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.conftest import WorkbenchServer  # noqa: E402
from tests.fixtures.demo_docx import build_plan_docx  # noqa: E402

# 脱敏示例文档：真实客户文档一律不许进截图（2026-10-20 合规要求）。
DEMO = Path(tempfile.gettempdir()) / "fox082"
DOCX = build_plan_docx(DEMO / "demo-plan.docx")
OUT = Path(__file__).resolve().parents[1] / "assets" / "screenshots" / "v0.8.1"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with WorkbenchServer(DEMO / "output") as server, \
            sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(server.base_url + "/")
        page.wait_for_function("window.FoxDocx && window.FoxIntake")
        page.evaluate("window.FoxIntake.open()")
        page.set_input_files("#docx-file", str(DOCX))
        page.click("#docx-analyze")
        page.wait_for_selector("#docx-proposal:not([hidden])", timeout=30000)
        page.wait_for_timeout(400)
        page.select_option("#docx-intent", "doc")
        page.screenshot(path=str(OUT / "docx-desk-proposal-1440.png"))
        page.click("#docx-adopt")
        page.wait_for_selector("#docx-result:not([hidden])", timeout=120000)
        href = page.get_attribute("#docx-result", "href")
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / "docx-desk-adopted-1440.png"))
        page.goto(server.base_url + href)
        page.wait_for_timeout(600)
        page.screenshot(path=str(OUT / "docx-artifact-1440.png"), full_page=False)
        print("preview:", href)
        print("sections:", page.evaluate("document.querySelectorAll('section').length"))

        # 同一份文档换个意图：审核台说改就改，产物形状跟着变（deck 不是长文档的翻版）
        page.goto(server.base_url + "/")
        page.wait_for_function("window.FoxDocx && window.FoxIntake")
        page.evaluate("window.FoxIntake.open()")
        page.set_input_files("#docx-file", str(DOCX))
        page.click("#docx-analyze")
        page.wait_for_selector("#docx-proposal:not([hidden])", timeout=30000)
        page.select_option("#docx-intent", "deck")
        page.click("#docx-adopt")
        page.wait_for_selector("#docx-result:not([hidden])", timeout=120000)
        deck_href = page.get_attribute("#docx-result", "href")
        page.goto(server.base_url + deck_href)
        page.wait_for_timeout(600)
        page.screenshot(path=str(OUT / "docx-artifact-deck-1440.png"))
        print("deck:", deck_href)
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
