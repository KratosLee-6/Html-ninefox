"""Word 审核台的浏览器门禁（v0.8.1 · step 3）。

真浏览器、真上传、真生成：解析出来的提案要能改，采纳后的产物里必须是 Word
自己的正文。API 单测覆盖不了「按钮接没接上」——v0.6.0 的死按钮就是漏在这。
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright
from test_docx_intake_api import build_docx

PROSE = "这是 Word 里的背景正文。"


def test_word_desk_uploads_reviews_and_adopts(workbench_server, tmp_path: Path):
    document = tmp_path / "季度交付说明.docx"
    document.write_bytes(build_docx())

    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(server.base_url + "/")
        page.wait_for_function("window.FoxDocx && window.FoxIntake")
        page.evaluate("window.FoxIntake.open()")

        page.set_input_files("#docx-file", str(document))
        page.click("#docx-analyze")
        page.wait_for_selector("#docx-proposal:not([hidden])", timeout=20000)

        assert page.input_value("#docx-headline") == "季度交付说明"
        assert page.eval_on_selector("#docx-intent", "el => el.options.length") >= 6
        assert page.eval_on_selector("#docx-preset", "el => el.options.length") >= 6
        assert page.eval_on_selector_all(
            "#docx-slots .docx-slot", "rows => rows.length") >= 1, "提案必须带图片位"
        assert page.is_visible("#docx-limits li"), "边界说明要在界面上可见"

        # 审核台说改就改：换意图＋换风格，产物要跟着变
        page.select_option("#docx-intent", "doc")
        page.click("#docx-adopt")
        page.wait_for_selector("#docx-result:not([hidden])", timeout=120000)

        href = page.get_attribute("#docx-result", "href")
        assert href and href.startswith("/output/")
        page.goto(server.base_url + href)
        assert PROSE in page.content(), "采纳后的产物必须带 Word 正文"
        assert not errors, f"页面脚本报错：{errors}"
        browser.close()
