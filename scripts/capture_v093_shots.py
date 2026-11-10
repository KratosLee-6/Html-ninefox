"""v0.9.3 发版取证：语气档案 + 润色保留用户说法（真实 UI 全链路）。

    evidence-voice-learn.png    记忆面板：粘贴素材学习语气后的状态（条数 + 纪律说明）
    evidence-polish-voice.png   推荐卡润色区：带语气档案的建议（勾选 + 可改文本）

全部走真实派发：按钮 → /api/voice-profile/learn → 档案落盘；润色走
/api/polish-slots（HTMLNINEFOX_LLM_STUB 确定性建议，真实门禁过滤）。
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

OUT = ROOT / "assets" / "screenshots" / "v0.9.3"

SAMPLES = """狐构交付的内容可以直接商用。狐构交付从不拖稿。
我们只做能直接拿去用的东西。狐构的看板一眼看清重点。"""


def main() -> int:
    os.environ["HTMLNINEFOX_LLM_STUB"] = "1"
    OUT.mkdir(parents=True, exist_ok=True)
    import tempfile

    from playwright.sync_api import sync_playwright

    from tests.conftest import WorkbenchServer

    with WorkbenchServer(Path(tempfile.mkdtemp())) as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1180, "height": 1000})
            page.goto(server.base_url + "/")
            page.wait_for_function("typeof window.FoxActions === 'object'")

            # 一、记忆面板：学习语气
            page.click("#btn-memory")
            page.wait_for_selector("#voice-samples", state="visible", timeout=15000)
            page.fill("#voice-samples", SAMPLES)
            page.click("#voice-learn")
            page.wait_for_function(
                "() => document.querySelector('#voice-status')?.textContent.includes('已学习')",
                timeout=15000)
            page.evaluate("typeof refreshVoiceStatus === 'function' && refreshVoiceStatus()")
            page.wait_for_timeout(300)
            # 滚到语气档案区并让状态栏进入视口，再截该区整段
            page.evaluate(
                "document.querySelector('#voice-status').scrollIntoView({block:'center'})")
            page.wait_for_timeout(250)
            page.locator("#memory-modal .flow-dialog").screenshot(
                path=OUT / "evidence-voice-learn.png")
            print("shot: evidence-voice-learn.png")

            # 二、推荐卡润色（档案已在服务端落盘，新会话也读得到）
            page.keyboard.press("Escape")
            page.click("#btn-create")
            page.wait_for_selector("#creation-prompt", state="visible", timeout=15000)
            page.fill("#creation-prompt",
                      "做一个狐构内容交付工作台的落地页，面向需要汇报的团队")
            page.click("#creation-analyze")
            page.wait_for_selector("[data-action=\"polishSlots\"]", timeout=30000)
            page.click("[data-action=\"polishSlots\"]")
            page.wait_for_function(
                "() => document.querySelector('#polish-result')?.innerHTML.includes('data-polish-key')",
                timeout=30000)
            page.wait_for_timeout(300)
            page.locator("#create-modal .flow-dialog").screenshot(
                path=OUT / "evidence-polish-voice.png")
            print("shot: evidence-polish-voice.png")
            browser.close()

    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
