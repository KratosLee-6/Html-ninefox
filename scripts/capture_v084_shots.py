"""v0.8.4 发版截图：审核台 PDF 提案 + 图片位挂真实图片（真服务器实拍）。"""
from __future__ import annotations

import base64
import io
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from playwright.sync_api import sync_playwright  # noqa: E402
from PIL import Image  # noqa: E402
from pptx import Presentation  # noqa: E402
from pptx.util import Inches  # noqa: E402

from tests.conftest import WorkbenchServer  # noqa: E402
from tests.test_pdf_import import build_pdf  # noqa: E402

OUT = ROOT / "assets" / "screenshots" / "v0.8.4"


def build_deck() -> bytes:
    prs = Presentation()
    prs.core_properties.title = "全域增长 Q4 汇报"
    cover = prs.slides.add_slide(prs.slide_layouts[0])
    cover.shapes.title.text = "全域增长 Q4 汇报"
    cover.placeholders[1].text = "面向管理层的季度汇报"
    plan = prs.slides.add_slide(prs.slide_layouts[1])
    plan.shapes.title.text = "三步走"
    body = plan.placeholders[1].text_frame
    body.text = "第一步：拉新"
    plan.notes_slide.notes_text_frame.text = "讲稿：预算与时间线。"
    buffer = io.BytesIO()
    prs.save(buffer)
    return buffer.getvalue()


def build_png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 360), (36, 62, 143)).save(buffer, format="PNG")
    return buffer.getvalue()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    pdf = tmp / "接入说明.pdf"
    pdf.write_bytes(build_pdf())
    deck = tmp / "全域增长Q4汇报.pptx"
    deck.write_bytes(build_deck())
    cover_png = tmp / "cover.png"
    cover_png.write_bytes(build_png())

    with WorkbenchServer(Path(tempfile.mkdtemp())) as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.goto(server.base_url + "/")
            page.wait_for_function("window.FoxDocx && window.FoxIntake")
            page.evaluate("window.FoxIntake.open()")

            # shot 1: PDF 提案
            page.set_input_files("#docx-file", str(pdf))
            page.click("#docx-analyze")
            page.wait_for_selector("#docx-proposal:not([hidden])", timeout=30000)
            page.wait_for_timeout(300)
            page.locator("#docx-desk").screenshot(
                path=OUT / "pdf-desk-proposal-1440.png")
            print("shot: pdf-desk-proposal-1440.png")

            # shot 2: PPT 上传 → cover 槽位附图 → 摘要 chip
            # （语言切换钮在提案渲染后才可见，放在首次分析之后）
            page.set_input_files("#docx-file", str(deck))
            page.click("#docx-analyze")
            page.wait_for_selector("#docx-proposal:not([hidden])", timeout=30000)
            page.click("#docx-slot-lang")  # 切 EN，槽位名与 plan id 对齐
            page.locator("#docx-slots .docx-slot").first.locator(
                ".docx-slot-attach input").set_input_files(str(cover_png))
            page.wait_for_selector("#docx-slots [data-part='asset']:not([hidden])",
                                   timeout=30000)
            page.wait_for_timeout(300)
            page.locator("#docx-desk").screenshot(
                path=OUT / "slot-attach-1440.png")
            print("shot: slot-attach-1440.png")
            browser.close()
    print("capture done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
