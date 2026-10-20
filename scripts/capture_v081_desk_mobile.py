"""Mobile-width shot of the Word desk (390px) — overlap check."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.conftest import WorkbenchServer  # noqa: E402
from tests.fixtures.demo_docx import build_plan_docx  # noqa: E402

DEMO = Path(tempfile.gettempdir()) / "fox082"
DOCX = build_plan_docx(DEMO / "demo-plan-mobile.docx")
OUT = Path(__file__).resolve().parents[1] / "assets" / "screenshots" / "v0.8.1"


def main() -> int:
    with WorkbenchServer(DEMO / "output-mobile") as server, \
            sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(server.base_url + "/")
        page.wait_for_function("window.FoxDocx && window.FoxIntake")
        page.evaluate("window.FoxIntake.open()")
        page.set_input_files("#docx-file", str(DOCX))
        page.click("#docx-analyze")
        page.wait_for_selector("#docx-proposal:not([hidden])", timeout=30000)
        page.wait_for_timeout(400)
        overflow = page.eval_on_selector_all(
            "#docx-desk *",
            """els => els.filter(el => {
              const r = el.getBoundingClientRect();
              return r.width > 0 && (r.right > innerWidth + 1 || r.left < -1);
            }).map(el => el.className || el.tagName).slice(0, 8)""")
        page.screenshot(path=str(OUT / "docx-desk-proposal-390.png"))
        print("overflow:", overflow or "none")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
