"""PPT 审核台的浏览器门禁（v0.8.3）。

镜像 test_docx_desk_ui 的纪律：真浏览器、真上传、真生成。重点断言两件
API 单测盖不住的事——同一张审核台按扩展名分流到 PPTX 端点，以及解析
边界（几何不还原）真的显示在界面上，而不是只躺在 JSON 里。
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright
from test_pptx_intake_api import build_pptx

PROSE = "第一步：拉新，渠道投放到位"
NOTES = "讲稿：强调预算与时间线的对应关系。"


def test_pptx_desk_uploads_reviews_and_adopts(workbench_server, tmp_path: Path):
    deck = tmp_path / "Q4汇报.pptx"
    deck.write_bytes(build_pptx())

    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(server.base_url + "/")
        page.wait_for_function("window.FoxDocx && window.FoxIntake")
        page.evaluate("window.FoxIntake.open()")

        page.set_input_files("#docx-file", str(deck))
        page.click("#docx-analyze")
        page.wait_for_selector("#docx-proposal:not([hidden])", timeout=20000)

        assert page.input_value("#docx-headline") == "增长团队 Q4 汇报"
        assert page.eval_on_selector("#docx-intent", "el => el.value") == "deck", \
            "pptx 来源的默认意图要在界面上就是 deck"
        limits_text = page.eval_on_selector_all(
            "#docx-limits li", "rows => rows.map(r => r.textContent).join('|')")
        assert "几何" in limits_text, "解析边界必须显示在界面上"

        # 审核台说改就改：人把意图换成 doc，产物要跟着变
        page.select_option("#docx-intent", "doc")
        page.click("#docx-adopt")
        page.wait_for_selector("#docx-result:not([hidden])", timeout=120000)

        href = page.get_attribute("#docx-result", "href")
        assert href and href.startswith("/output/")
        page.goto(server.base_url + href)
        assert PROSE in page.content(), "采纳后的产物必须带幻灯片要点"
        assert NOTES in page.content(), "讲稿备注也要到产物里"
        assert not errors, f"页面脚本报错：{errors}"
        browser.close()
